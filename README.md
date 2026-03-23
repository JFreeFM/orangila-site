# OranGila Site

Static website project for `orangila.com`.

## Structure

- `site/` contains the published website files.
- `scripts/` contains local build, deploy, and status update helpers.

## Deploy

Deploy from the project root with:

```bash
./scripts/deploy_transip.sh
```

Environment-specific deploy settings belong in `.env.deploy` and are not tracked.

## Public Repo Rules

This repository is meant to stay public.

Keep public:
- website source in `site/`
- generic deploy/build helpers
- public status page output

Keep private:
- `.env.deploy`
- tokens, passwords, webhook URLs, and private SSH material
- internal ops snapshots or host-specific run notes
- environment-specific paths unless they are required for local runtime only

If local infrastructure details are needed, prefer env vars or non-tracked local config.
