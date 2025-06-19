import atexit
import io
import json
import threading
import time
from typing import Any, Dict, Tuple

import numpy as np
import uvicorn
from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image


class ImageServer:
    def __init__(self):
        self.app = FastAPI()
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._current_probe_data = None
        self._server = None
        self._server_thread = None

        atexit.register(self.stop)

        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.post("/capture")
        async def capture(request: Request):
            print("Capture endpoint called")
            current_time = time.time()
            try:
                contents = None
                content_type = request.headers.get("content-type", "").lower()

                if content_type.startswith("multipart/form-data"):
                    form = await request.form()
                    file_upload = form.get("file")
                    if not file_upload or not isinstance(file_upload, UploadFile):
                        print("No file uploaded in form")
                        return {"status": "error", "message": "No file uploaded"}
                    contents = await file_upload.read()
                elif content_type.startswith("image/"):
                    contents = await request.body()
                    if not contents:
                        print("No image data in request body")
                        return {
                            "status": "error",
                            "message": "No image data in request body",
                        }
                else:
                    print(f"Unsupported content type: {content_type}")
                    return {
                        "status": "error",
                        "message": f"Unsupported content type: {content_type}",
                    }

                image = Image.open(io.BytesIO(contents))
                image_array = np.array(image)

                metadata = {}
                x_metadata = request.headers.get("x-metadata")
                x_metadata_content_type = request.headers.get("x-metadata-content-type")
                print(f"X-Metadata: {x_metadata}")
                print(f"X-Metadata-Content-Type: {x_metadata_content_type}")
                if x_metadata and x_metadata_content_type == "application/json":
                    try:
                        metadata = json.loads(x_metadata)
                    except json.JSONDecodeError:
                        metadata = {
                            "error": "Invalid X-Metadata format",
                            "raw": x_metadata,
                        }

                metadata["epoch"] = current_time

                with self._lock:
                    self._current_probe_data = (image_array, metadata)
                    self._event.set()
                    print(f"New image captured: {self._current_probe_data}")
                return {"status": "success"}
            except Exception as e:
                print(f"Error in capture endpoint: {str(e)}")
                return {"status": "error", "message": str(e)}

    def start(self, host: str = "0.0.0.0", port: int = 3000):
        config = uvicorn.Config(self.app, host=host, port=port, log_level="error")
        self._server = uvicorn.Server(config)
        self._server_thread = threading.Thread(target=self._server.run)
        self._server_thread.daemon = True
        self._server_thread.start()
        print(f"ImageServer started on {host}:{port}/capture")

    def stop(self):
        if self._server:
            self._server.should_exit = True
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5)
            self._server = None
            self._server_thread = None
            print("ImageServer stopped.")

    def get_next_image(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        self._event.wait()
        with self._lock:
            image_data = self._current_probe_data
            self._current_probe_data = None
            self._event.clear()
        return np.mean(image_data[0], axis=2), image_data[1]
