import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run the Ratatosk API server.")
    parser.add_argument(
        "--is-private", action="store_true", help="Run the server in private mode."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000).",
    )

    args = parser.parse_args()

    host = "0.0.0.0"

    if args.is_private:
        host = "127.0.0.1"

    uvicorn.run(
        "ratatosk.app:app",
        host=host,
        port=args.port,
        reload=True,
    )
