# OranGila Site

Static website project for `orangila.com`, managed on this server.

## Deploy

The live target is TransIP. Deploy from the project root with:

```bash
./scripts/deploy_transip.sh
```

## Notes

- `site/` contains the published website files.
- `scripts/deploy_transip.sh` handles deployment to TransIP.
- Environment-specific deploy settings belong in `.env.deploy` and are not tracked.

## Git Remote

If you want to connect this repository to a remote later, add one manually:

```bash
git remote add origin <your-remote-url>
```
