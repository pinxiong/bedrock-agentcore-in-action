"""Independence helper used by every use case's smoke test.

Implements assertion I2 from README's independence contract: after `python aia.py down`,
no resource tagged with another use case's number may exist because of this run.

Requires boto3 and working credentials. Set AWS_REGION if you do not use us-east-1.

This file is copied into each use case by `aia.py new` rather
than imported, so that use cases stay independent of one another (contract I4).
"""

from __future__ import annotations

import os

REGION = os.environ.get("AWS_REGION", "us-east-1")
PROJECT = "agentcore-in-action"


def _client():
    try:
        import boto3  # imported lazily so the rest of the test file imports cleanly
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "the independence check needs boto3. fix: pip install boto3"
        ) from exc

    from botocore.exceptions import NoCredentialsError  # noqa: F401

    try:
        client = boto3.client("resourcegroupstaggingapi", region_name=REGION)
        client.get_resources(TagFilters=[], ResourcesPerPage=1)
        return client
    except NoCredentialsError as exc:
        raise AssertionError(
            "the independence check needs AWS credentials. "
            "fix: run `aws sts get-caller-identity`, then re-run `aia test`"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"the independence check could not reach Resource Groups Tagging API in "
            f"{REGION}: {exc.__class__.__name__}: {exc}"
        ) from exc


def resources_for(use_case_numbers: list[str]) -> list[str]:
    """ARNs tagged with Project=agentcore-in-action and UseCase in the given list."""
    if not use_case_numbers:
        return []
    resp = _client().get_resources(
        TagFilters=[
            {"Key": "Project", "Values": [PROJECT]},
            {"Key": "UseCase", "Values": use_case_numbers},
        ],
    )
    return [m["ResourceARN"] for m in resp.get("ResourceTagMappingList", [])]


def check_other_use_cases(own: str, others: list[str]) -> None:
    found = resources_for(others)
    if found:
        listing = "\n    ".join(found[:10])
        raise AssertionError(
            f"{own} created resources belonging to other use cases "
            f"({len(found)} found), which breaks independence:\n    {listing}"
        )


def own_resources(use_case_number: str) -> list[str]:
    return resources_for([use_case_number])
