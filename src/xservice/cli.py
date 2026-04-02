
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Main entry point for the xservice CLI.
    """
    parser = argparse.ArgumentParser(description="A CLI for the xservice API.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("XSERVICE_BASE_URL", "http://localhost:8000/api/v1"),
        help="The base URL for the xservice API. Can also be set with XSERVICE_BASE_URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("XSERVICE_API_KEY"),
        help="The API key for the xservice API. Can also be set with XSERVICE_API_KEY.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Health command
    subparsers.add_parser("health", help="Check the health of the API.")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for content.")
    search_parser.add_argument("query", help="The search query.")
    search_parser.add_argument(
        "--category", action="append", help="Category to filter search by."
    )
    search_parser.add_argument(
        "--limit", type=int, help="The maximum number of results to return."
    )

    # User command
    user_parser = subparsers.add_parser("user", help="User-related commands.")
    user_subparsers = user_parser.add_subparsers(dest="user_command", required=True)

    user_commands = {
        "profile": False,
        "timeline": True,
        "tweets": True,
        "followers": True,
        "following": True,
        "likes": True,
        "media": True,
        "tweets-and-replies": True,
    }
    for cmd, has_limit in user_commands.items():
        user_cmd_parser = user_subparsers.add_parser(
            cmd, help=f"Get user's {cmd.replace('-', ' ')}."
        )
        user_cmd_parser.add_argument("username", help="The username.")
        if has_limit:
            user_cmd_parser.add_argument(
                "--limit", type=int, help="The maximum number of results to return."
            )

    # Tweet command
    tweet_parser = subparsers.add_parser("tweet", help="Tweet-related commands.")
    tweet_subparsers = tweet_parser.add_subparsers(
        dest="tweet_command", required=True
    )

    # Tweet subcommands
    tweet_detail_parser = tweet_subparsers.add_parser(
        "detail", help="Get details for a specific tweet."
    )
    tweet_detail_parser.add_argument("tweet_id", help="The tweet ID.")

    tweet_retweeters_parser = tweet_subparsers.add_parser(
        "retweeters", help="Get users who retweeted a tweet."
    )
    tweet_retweeters_parser.add_argument("tweet_id", help="The tweet ID.")
    tweet_retweeters_parser.add_argument(
        "--limit", type=int, help="The maximum number of results to return."
    )

    tweet_favoriters_parser = tweet_subparsers.add_parser(
        "favoriters", help="Get users who favorited a tweet."
    )
    tweet_favoriters_parser.add_argument("tweet_id", help="The tweet ID.")
    tweet_favoriters_parser.add_argument(
        "--limit", type=int, help="The maximum number of results to return."
    )

    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    path = ""
    params = {}

    if args.command == "health":
        path = "/health/"
    elif args.command == "search":
        path = "/search/"
        params["q"] = args.query
        if args.category:
            params["category"] = args.category
        if args.limit:
            params["limit"] = args.limit
    elif args.command == "user":
        path_segment = args.user_command.replace("-", "_")
        if path_segment == "profile":
             path = f"/users/{args.username}/"
        else:
             path = f"/users/{args.username}/{path_segment}/"

        if hasattr(args, "limit") and args.limit:
            params["limit"] = args.limit

    elif args.command == "tweet":
        path = f"/tweets/{args.tweet_id}/"
        if args.tweet_command != "detail":
            path += f"{args.tweet_command}/"
        if hasattr(args, "limit") and args.limit:
            params["limit"] = args.limit

    url = f"{base_url}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)

    headers = {"Accept": "application/json"}
    if args.api_key:
        headers["X-API-KEY"] = args.api_key

    try:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request) as response:
            if response.status >= 400:
                print(f"Error: Received status code {response.status}", file=sys.stderr)
                return 1
            data = json.load(response)
            print(json.dumps(data, indent=2))
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} {e.reason}", file=sys.stderr)
        try:
            error_body = json.loads(e.read())
            print(json.dumps(error_body, indent=2), file=sys.stderr)
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        return 1
    except urllib.error.URLError as e:
        print(f"Error: {e.reason}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
