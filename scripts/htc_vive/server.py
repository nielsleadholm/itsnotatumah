#!/usr/bin/env python3
"""
Pose logger for a VIVE Tracker 3.0 (no HMD).
Provides pose via HTTP endpoint (quaternion and position).
"""

import json
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import numpy as np
import openvr
from scipy.spatial.transform import Rotation

# Global variable to store the latest pose data and a lock for thread-safe access
latest_pose_data = {
    "timestamp": 0.0,
    "pose_matrix": None,
    "is_valid": False,
    "serial_number": "",
}
pose_lock = threading.Lock()
shutdown_event = threading.Event()


# -----------------------------------------------------------------------------#
# Helpers
# -----------------------------------------------------------------------------#
def find_first_tracker_index(vr_sys):
    """Return the index of the first GenericTracker i.e. VIVE Tracker device."""
    # Iterate over all devices, e.g. any head-mounted display (HMD), controller, or
    # tracker
    for i in range(openvr.k_unMaxTrackedDeviceCount):
        # GenericTracker is the only device class that will correspond to a VIVE Tracker
        if vr_sys.getTrackedDeviceClass(i) != openvr.TrackedDeviceClass_GenericTracker:
            continue
        return i
    return None


# -----------------------------------------------------------------------------#
# Vive Tracker Thread
# -----------------------------------------------------------------------------#
class ViveTrackerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.name = "ViveTrackerThread"

    def run(self):
        global latest_pose_data
        vr_sys = None
        try:
            openvr.init(openvr.VRApplication_Other)
            vr_sys = openvr.VRSystem()
            print("OpenVR initialized in ViveTrackerThread.")

            tracker_index = find_first_tracker_index(vr_sys)
            if tracker_index is None:
                print(
                    "No VIVE Tracker detected. Check if it is powered on and in view of the base-stations."
                )
                with pose_lock:
                    latest_pose_data["is_valid"] = False
                return

            serial = vr_sys.getStringTrackedDeviceProperty(
                tracker_index, openvr.Prop_SerialNumber_String
            )
            print(f"Using tracker index {tracker_index} (serial {serial})")
            with pose_lock:
                latest_pose_data["serial_number"] = serial

            while not shutdown_event.is_set():
                current_time_epoch = time.time()
                poses = vr_sys.getDeviceToAbsoluteTrackingPose(
                    openvr.TrackingUniverseStanding,
                    0,  # Don't predict a future pose, instead get it from now (0 seconds in future)
                    openvr.k_unMaxTrackedDeviceCount,
                )
                p = poses[tracker_index]

                # Create list of lists from the pose matrix
                pose_matrix = [
                    [float(val) for val in row] for row in p.mDeviceToAbsoluteTracking
                ]

                with pose_lock:
                    latest_pose_data["timestamp"] = current_time_epoch
                    latest_pose_data["pose_matrix"] = pose_matrix
                    latest_pose_data["is_valid"] = p.bPoseIsValid

                if p.bPoseIsValid:
                    # Print to console for debugging
                    # print(f"time={current_time_epoch:.3f} with pose matrix:")
                    # print(pose_matrix)
                    pass

                else:
                    # print(f"time={current_time_epoch:.3f} Tracker pose not valid")
                    pass

                time.sleep(0.01)  # Loop at approx 100Hz, adjust as needed

        except openvr.OpenVRError as e:
            print(f"OpenVR Error in ViveTrackerThread: {e}", file=sys.stderr)
            with pose_lock:
                latest_pose_data["is_valid"] = False
        except Exception as e:
            print(
                f"An unexpected error occurred in ViveTrackerThread: {e}",
                file=sys.stderr,
            )
            with pose_lock:
                latest_pose_data["is_valid"] = False
        finally:
            if vr_sys:
                print("Shutting down OpenVR in ViveTrackerThread...")
                openvr.shutdown()
            print("ViveTrackerThread finished.")


# -----------------------------------------------------------------------------#
# HTTP Server
# -----------------------------------------------------------------------------#
class PoseHTTPRequestHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        """Set CORS headers to allow cross-origin requests from web browsers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "3600")

    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests for CORS."""
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        global latest_pose_data

        print(f"Received GET request from {self.client_address[0]} for {self.path}")

        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/pose":
            # response_data = {
            #     "data": {
            #         "timestamp": time.time(),
            #         "pose": {
            #             "position": {"x": 0.1, "y": 0.2, "z": 0.3},
            #             "rotation": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
            #         },
            #         "serial_number": "FAKE_SERIAL_123",
            #     }
            # }
            # self.send_response(200)
            # self.send_header("Content-type", "application/json")
            # self.end_headers()
            # self.wfile.write(json.dumps(response_data).encode("utf-8"))
            # return

            # query_params = urllib.parse.parse_qs(parsed_path.query)
            # requested_epoch = query_params.get('epoch', [None])[0]
            # For now, we ignore requested_epoch and return the latest

            with pose_lock:
                timestamp = latest_pose_data["timestamp"]
                pose_matrix = latest_pose_data["pose_matrix"]
                is_valid = latest_pose_data["is_valid"]

            if is_valid and pose_matrix:
                try:
                    # Position
                    pos_x = pose_matrix[0][3]
                    pos_y = pose_matrix[1][3]
                    pos_z = pose_matrix[2][3]
                    position = {"x": pos_x, "y": pos_y, "z": pos_z}

                    # Rotation
                    rotation_mtx = np.array([row[:3] for row in pose_matrix[:3]])
                    r = Rotation.from_matrix(rotation_mtx)
                    quat_xyzw = r.as_quat()  # SciPy returns [x, y, z, w]

                    rotation_quat = {
                        "w": quat_xyzw[3],  # qw
                        "x": quat_xyzw[0],  # qx
                        "y": quat_xyzw[1],  # qy
                        "z": quat_xyzw[2],  # qz
                    }

                    response_data = {
                        "data": {
                            "timestamp": timestamp,
                            "pose": {
                                "position": position,
                                "rotation": rotation_quat,
                            },
                            "serial_number": latest_pose_data.get("serial_number", ""),
                        }
                    }
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode("utf-8"))
                except Exception as e:
                    print(f"Error processing pose data for HTTP response: {e}")
                    self.send_response(500)
                    self.send_header("Content-type", "application/json")
                    self._set_cors_headers()
                    self.end_headers()
                    error_payload = {
                        "error": "Internal server error processing pose data",
                        "details": str(e),
                    }
                    self.wfile.write(json.dumps(error_payload).encode("utf-8"))

            else:
                self.send_response(404)  # Or 503 Service Unavailable
                self.send_header("Content-type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                error_payload = {"error": "Tracker pose not available or invalid"}
                if latest_pose_data.get("serial_number"):
                    error_payload["serial_number"] = latest_pose_data["serial_number"]
                self.wfile.write(json.dumps(error_payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b"Endpoint not found. Use /pose")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

    daemon_threads = (
        True  # Allow main thread to exit even if server threads are running
    )


# -----------------------------------------------------------------------------#
# Main
# -----------------------------------------------------------------------------#
def main():
    # Start the Vive Tracker thread
    tracker_thread = ViveTrackerThread()
    tracker_thread.daemon = (
        True  # Allow main program to exit even if this thread is running
    )
    tracker_thread.start()
    print("ViveTrackerThread started.")

    # Start the HTTP server
    server_address = ("0.0.0.0", 3001)
    httpd = ThreadingHTTPServer(server_address, PoseHTTPRequestHandler)
    print(f"HTTP server listening on {server_address[0]}:{server_address[1]}...")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, shutting down...")
    finally:
        shutdown_event.set()  # Signal ViveTrackerThread to stop
        print("Shutting down HTTP server...")
        httpd.shutdown()  # Stop the HTTP server
        httpd.server_close()  # Release the port
        print("Waiting for ViveTrackerThread to join...")
        tracker_thread.join(timeout=5)  # Wait for the tracker thread to finish
        if tracker_thread.is_alive():
            print("ViveTrackerThread did not join in time.")
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
