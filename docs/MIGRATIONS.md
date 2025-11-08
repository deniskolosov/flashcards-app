# Database Migrations with Alembic

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

## Common Commands

### Check Migration Status
```bash
uv run alembic current
```

### View Migration History
```bash
uv run alembic history
```

### Create a New Migration
```bash
# Auto-generate migration based on model changes
uv run alembic revision --autogenerate -m "description_of_changes"

# Create empty migration template
uv run alembic revision -m "description_of_changes"
```

### Apply Migrations
```bash
# Apply all pending migrations
uv run alembic upgrade head

# Apply migrations up to specific revision
uv run alembic upgrade <revision_id>
```

### Rollback Migrations
```bash
# Rollback to previous revision
uv run alembic downgrade -1

# Rollback to specific revision
uv run alembic downgrade <revision_id>

# Rollback all migrations
uv run alembic downgrade base
```

## Configuration

- **Database URL**: Configured in `alembic.ini`
- **Models**: Auto-imported from `backend.models.Base` in `alembic/env.py`
- **Migration Files**: Stored in `alembic/versions/`

## Migration Workflow

1. **Make changes to models** in `backend/models.py`
2. **Generate migration**: `uv run alembic revision --autogenerate -m "description"`
3. **Review the generated migration** in `alembic/versions/`
4. **Apply the migration**: `uv run alembic upgrade head`
5. **Test** that the application works with the new schema

## Important Notes

- Always review auto-generated migrations before applying them
- Test migrations on a copy of production data first
- Consider data migrations for complex schema changes
- Add appropriate default values for new NOT NULL columns
- Backup your database before applying migrations in production

## Example: Adding a New Field

1. Add the field to your model:
```python
# backend/models.py
class MyModel(Base):
    # ... existing fields ...
    new_field: Mapped[str] = mapped_column(String(100), nullable=True)
```

2. Generate migration:
```bash
uv run alembic revision --autogenerate -m "add_new_field_to_my_model"
```

3. Review and edit the generated migration if needed
4. Apply the migration:
```bash
uv run alembic upgrade head
```

## Current Schema Version

The current schema includes:
- Initial baseline schema with spaced repetition fields (ease_factor, interval_days, repetitions)
- Revision: f3e3ac684f8e