"""Import every module's models so Base.metadata is complete for Alembic autogenerate."""

from app.core.db import Base
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.batch import models as batch_models  # noqa: F401
from app.modules.iam import models as iam_models  # noqa: F401
from app.modules.material import models as material_models  # noqa: F401
from app.modules.mutation import models as mutation_models  # noqa: F401
from app.modules.product import models as product_models  # noqa: F401
from app.modules.recipe import models as recipe_models  # noqa: F401
from app.modules.signature import models as signature_models  # noqa: F401
from app.modules.vault import models as vault_models  # noqa: F401

metadata = Base.metadata
