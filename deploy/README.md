# Production deployment artifacts

`python tools/build_deployment.py build` generates ARM templates and `manifest.json`
from the actual compiler output. The signed workflow snapshot contains the generated
identity/network production packs. Deploy that verified snapshot rather than rebuilding
templates in the Azure job. See `governance/repository-governance.md` for environment,
OIDC, review and live Azure validation prerequisites.
