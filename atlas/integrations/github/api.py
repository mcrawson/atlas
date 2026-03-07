"""
GitHub API client for ATLAS Transporter.

Provides async HTTP client for GitHub API operations using httpx.
Follows the K.I.T.T. pattern from atlas/integrations/slack.py.
"""

import logging
from typing import Any, Optional

import httpx

from .models import (
    TransporterConfig,
    GitHubIssueData,
    GitHubCommentData,
)

logger = logging.getLogger(__name__)

# Singleton instance
_github_api: Optional["GitHubAPI"] = None


def get_github_api(config: Optional[TransporterConfig] = None) -> "GitHubAPI":
    """Get or create the global GitHub API client instance.

    Args:
        config: Optional configuration. Uses env vars if not provided.

    Returns:
        GitHubAPI instance
    """
    global _github_api
    if _github_api is None:
        _github_api = GitHubAPI(config)
    return _github_api


class GitHubAPI:
    """Async HTTP client for GitHub API.

    Handles authentication, rate limiting, and error handling.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, config: Optional[TransporterConfig] = None):
        """Initialize the GitHub API client.

        Args:
            config: Configuration with token and settings
        """
        self.config = config or TransporterConfig.from_env()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if self.config.token:
                headers["Authorization"] = f"Bearer {self.config.token}"

            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _parse_repo(self, repo: str) -> tuple[str, str]:
        """Parse owner/repo string into tuple.

        Args:
            repo: Repository in "owner/repo" format

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            ValueError: If repo format is invalid
        """
        if "/" not in repo:
            raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/repo'")
        parts = repo.split("/", 1)
        return parts[0], parts[1]

    # Issue operations

    async def get_issue(self, repo: str, issue_number: int) -> Optional[GitHubIssueData]:
        """Get a GitHub issue by number.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number

        Returns:
            GitHubIssueData or None if not found
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues/{issue_number}"

        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return GitHubIssueData.from_github_response(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error getting issue {repo}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error getting issue {repo}#{issue_number}: {e}")
            raise

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] = None,
        assignees: list[str] = None,
        milestone: Optional[int] = None,
    ) -> GitHubIssueData:
        """Create a new GitHub issue.

        Args:
            repo: Repository in "owner/repo" format
            title: Issue title
            body: Issue body (markdown)
            labels: List of label names
            assignees: List of usernames to assign
            milestone: Milestone number

        Returns:
            Created GitHubIssueData
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues"

        payload: dict[str, Any] = {
            "title": title,
            "body": body,
        }
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        if milestone:
            payload["milestone"] = milestone

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return GitHubIssueData.from_github_response(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error creating issue in {repo}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error creating issue in {repo}: {e}")
            raise

    async def update_issue(
        self,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[list[str]] = None,
        assignees: Optional[list[str]] = None,
        milestone: Optional[int] = None,
    ) -> GitHubIssueData:
        """Update an existing GitHub issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            title: New title (optional)
            body: New body (optional)
            state: New state: "open" or "closed" (optional)
            labels: New labels (optional)
            assignees: New assignees (optional)
            milestone: New milestone number (optional)

        Returns:
            Updated GitHubIssueData
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues/{issue_number}"

        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        if assignees is not None:
            payload["assignees"] = assignees
        if milestone is not None:
            payload["milestone"] = milestone

        try:
            response = await self.client.patch(url, json=payload)
            response.raise_for_status()
            return GitHubIssueData.from_github_response(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error updating issue {repo}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error updating issue {repo}#{issue_number}: {e}")
            raise

    async def close_issue(self, repo: str, issue_number: int) -> GitHubIssueData:
        """Close a GitHub issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number

        Returns:
            Updated GitHubIssueData
        """
        return await self.update_issue(repo, issue_number, state="closed")

    async def reopen_issue(self, repo: str, issue_number: int) -> GitHubIssueData:
        """Reopen a closed GitHub issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number

        Returns:
            Updated GitHubIssueData
        """
        return await self.update_issue(repo, issue_number, state="open")

    # Comment operations

    async def get_comments(
        self, repo: str, issue_number: int, per_page: int = 30
    ) -> list[GitHubCommentData]:
        """Get comments on a GitHub issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            per_page: Number of comments per page

        Returns:
            List of GitHubCommentData
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues/{issue_number}/comments"

        try:
            response = await self.client.get(url, params={"per_page": per_page})
            response.raise_for_status()
            return [GitHubCommentData.from_github_response(c) for c in response.json()]
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error getting comments for {repo}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error getting comments for {repo}#{issue_number}: {e}")
            raise

    async def create_comment(
        self, repo: str, issue_number: int, body: str
    ) -> GitHubCommentData:
        """Create a comment on a GitHub issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            body: Comment body (markdown)

        Returns:
            Created GitHubCommentData
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues/{issue_number}/comments"

        try:
            response = await self.client.post(url, json={"body": body})
            response.raise_for_status()
            return GitHubCommentData.from_github_response(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error creating comment on {repo}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error creating comment on {repo}#{issue_number}: {e}")
            raise

    async def update_comment(
        self, repo: str, comment_id: int, body: str
    ) -> GitHubCommentData:
        """Update an existing comment.

        Args:
            repo: Repository in "owner/repo" format
            comment_id: Comment ID
            body: New comment body

        Returns:
            Updated GitHubCommentData
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues/comments/{comment_id}"

        try:
            response = await self.client.patch(url, json={"body": body})
            response.raise_for_status()
            return GitHubCommentData.from_github_response(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error updating comment {comment_id} in {repo}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error updating comment {comment_id} in {repo}: {e}")
            raise

    # Label operations

    async def add_labels(
        self, repo: str, issue_number: int, labels: list[str]
    ) -> list[str]:
        """Add labels to an issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            labels: List of label names to add

        Returns:
            List of all labels now on the issue
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues/{issue_number}/labels"

        try:
            response = await self.client.post(url, json={"labels": labels})
            response.raise_for_status()
            return [label["name"] for label in response.json()]
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error adding labels to {repo}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error adding labels to {repo}#{issue_number}: {e}")
            raise

    async def remove_label(
        self, repo: str, issue_number: int, label: str
    ) -> bool:
        """Remove a label from an issue.

        Args:
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            label: Label name to remove

        Returns:
            True if label was removed
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues/{issue_number}/labels/{label}"

        try:
            response = await self.client.delete(url)
            return response.status_code == 200
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error removing label from {repo}#{issue_number}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error removing label from {repo}#{issue_number}: {e}")
            raise

    # Repository operations

    async def list_issues(
        self,
        repo: str,
        state: str = "open",
        labels: Optional[list[str]] = None,
        per_page: int = 30,
    ) -> list[GitHubIssueData]:
        """List issues in a repository.

        Args:
            repo: Repository in "owner/repo" format
            state: Issue state: "open", "closed", or "all"
            labels: Filter by labels
            per_page: Number of issues per page

        Returns:
            List of GitHubIssueData
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/issues"

        params: dict[str, Any] = {
            "state": state,
            "per_page": per_page,
        }
        if labels:
            params["labels"] = ",".join(labels)

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Filter out pull requests (they appear in issues endpoint)
            issues = [
                GitHubIssueData.from_github_response(i)
                for i in response.json()
                if "pull_request" not in i
            ]
            return issues
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error listing issues in {repo}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error listing issues in {repo}: {e}")
            raise

    # Repository operations

    async def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
        gitignore_template: Optional[str] = None,
        license_template: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new GitHub repository.

        Args:
            name: Repository name
            description: Repository description
            private: Whether repo should be private
            auto_init: Initialize with README
            gitignore_template: Name of gitignore template (e.g., "Python", "Node")
            license_template: Name of license template (e.g., "mit", "apache-2.0")

        Returns:
            Created repository data
        """
        url = "/user/repos"

        payload: dict[str, Any] = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        if gitignore_template:
            payload["gitignore_template"] = gitignore_template
        if license_template:
            payload["license_template"] = license_template

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"Created repository: {response.json()['full_name']}")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error creating repo {name}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error creating repo {name}: {e}")
            raise

    async def get_repo(self, repo: str) -> Optional[dict[str, Any]]:
        """Get repository information.

        Args:
            repo: Repository in "owner/repo" format

        Returns:
            Repository data or None if not found
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}"

        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error getting repo {repo}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error getting repo {repo}: {e}")
            raise

    async def create_or_update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create or update a file in a repository.

        Args:
            repo: Repository in "owner/repo" format
            path: File path in repository
            content: File content (will be base64 encoded)
            message: Commit message
            branch: Branch name (default: main)
            sha: SHA of file being updated (required for updates)

        Returns:
            Commit data
        """
        import base64

        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/contents/{path}"

        # Base64 encode content
        content_encoded = base64.b64encode(content.encode()).decode()

        payload: dict[str, Any] = {
            "message": message,
            "content": content_encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            response = await self.client.put(url, json=payload)
            response.raise_for_status()
            logger.info(f"Created/updated file: {repo}/{path}")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error creating file {path} in {repo}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error creating file {path} in {repo}: {e}")
            raise

    async def get_file(
        self,
        repo: str,
        path: str,
        branch: str = "main",
    ) -> Optional[dict[str, Any]]:
        """Get a file from a repository.

        Args:
            repo: Repository in "owner/repo" format
            path: File path in repository
            branch: Branch name (default: main)

        Returns:
            File data including SHA (needed for updates) or None if not found
        """
        owner, repo_name = self._parse_repo(repo)
        url = f"/repos/{owner}/{repo_name}/contents/{path}"

        try:
            response = await self.client.get(url, params={"ref": branch})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error getting file {path} from {repo}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error getting file {path} from {repo}: {e}")
            raise

    async def push_files(
        self,
        repo: str,
        files: dict[str, str],
        message: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Push multiple files to a repository.

        Args:
            repo: Repository in "owner/repo" format
            files: Dict of {path: content}
            message: Commit message
            branch: Branch name (default: main)

        Returns:
            List of commit results
        """
        results = []
        for path, content in files.items():
            # Check if file exists to get SHA
            existing = await self.get_file(repo, path, branch)
            sha = existing.get("sha") if existing else None

            result = await self.create_or_update_file(
                repo=repo,
                path=path,
                content=content,
                message=f"{message}: {path}",
                branch=branch,
                sha=sha,
            )
            results.append(result)
        return results

    async def get_user(self) -> dict[str, Any]:
        """Get the authenticated user's information.

        Returns:
            User data including login (username)
        """
        try:
            response = await self.client.get("/user")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error getting user: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error getting user: {e}")
            raise

    # Utility methods

    async def check_rate_limit(self) -> dict[str, Any]:
        """Check GitHub API rate limit status.

        Returns:
            Rate limit information
        """
        try:
            response = await self.client.get("/rate_limit")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Error checking rate limit: {e}")
            raise
