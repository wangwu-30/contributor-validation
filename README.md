# Public contribution validation

This repository runs bounded Linux checks for a public SGLang contribution candidate.
It is not an upstream SGLang pull request or a claim of merged contribution.

The first batch uses upstream commit `76dafba55a5e3e155368474fe9ffcdc71db27749`
and patch SHA-256 `35b4e8a8e07a848a284d8d72569583a8a15d0b53ca1adafe4d28791e51b93763`.
It runs the unchanged upstream `pre-commit run --all-files` configuration on Linux.
If the candidate fails, the same base is checked separately to identify pre-existing failures.
A matching baseline failure is reported as a failure, never as a passing candidate.

Only the public repository's standard `ubuntu-24.04` runner is used.
There are no larger runners, uploaded artifacts, persistent build caches, models,
GPU jobs, credentials in inputs, or user session uploads.
Full test evidence is compressed into the job log with a SHA-256 digest for local archival.
The product patch is under SGLang's upstream Apache-2.0 license.
