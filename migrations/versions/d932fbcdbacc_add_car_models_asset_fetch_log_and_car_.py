"""Add car_models, asset_fetch_log, and car_images metadata

Revision ID: d932fbcdbacc
Revises: 8fb48a88edc9
Create Date: 2026-11-22 18:47:32.503067

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd932fbcdbacc'
down_revision = '8fb48a88edc9'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'asset_fetch_log' not in existing_tables:
        op.create_table('asset_fetch_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('car_slug', sa.String(length=160), nullable=True),
        sa.Column('asset_type', sa.String(length=30), nullable=False),
        sa.Column('source_name', sa.String(length=80), nullable=False),
        sa.Column('query', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
        )
        with op.batch_alter_table('asset_fetch_log', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_asset_fetch_log_car_slug'), ['car_slug'], unique=False)

    if 'car_models' not in existing_tables:
        op.create_table('car_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('file_format', sa.String(length=20), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('poly_count', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=80), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('author', sa.String(length=160), nullable=False),
        sa.Column('license', sa.String(length=80), nullable=False),
        sa.Column('license_url', sa.String(length=500), nullable=True),
        sa.Column('body_material_names', sa.JSON(), nullable=True),
        sa.Column('scale', sa.Float(), nullable=False),
        sa.Column('offset_y', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
        )
        with op.batch_alter_table('car_models', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_car_models_car_id'), ['car_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_car_models_sha256'), ['sha256'], unique=False)

    existing_cols = {c['name'] for c in insp.get_columns('car_images')}
    existing_idxs = {ix['name'] for ix in insp.get_indexes('car_images')}
    cols_to_add = [
        ('sha256', sa.Column('sha256', sa.String(length=64), nullable=True)),
        ('phash', sa.Column('phash', sa.String(length=32), nullable=True)),
        ('width', sa.Column('width', sa.Integer(), nullable=True)),
        ('height', sa.Column('height', sa.Integer(), nullable=True)),
        ('file_size', sa.Column('file_size', sa.Integer(), nullable=True)),
        ('is_hero', sa.Column('is_hero', sa.Boolean(), nullable=False, server_default='0')),
        ('is_active', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1')),
        ('sort_order', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0')),
        ('shot_type', sa.Column('shot_type', sa.String(length=30), nullable=False, server_default='exterior')),
        ('caption', sa.Column('caption', sa.String(length=255), nullable=True)),
        ('match_level', sa.Column('match_level', sa.String(length=20), nullable=False, server_default='exact')),
        ('source_name', sa.Column('source_name', sa.String(length=80), nullable=True)),
        ('source_id', sa.Column('source_id', sa.String(length=160), nullable=True)),
        ('image_blob', sa.Column('image_blob', sa.LargeBinary(length=4294967295), nullable=True)),
        ('fetched_at', sa.Column('fetched_at', sa.DateTime(), nullable=True)),
    ]
    with op.batch_alter_table('car_images', schema=None) as batch_op:
        for cname, col in cols_to_add:
            if cname not in existing_cols:
                batch_op.add_column(col)
        if 'ix_car_images_phash' not in existing_idxs:
            batch_op.create_index(batch_op.f('ix_car_images_phash'), ['phash'], unique=False)
        if 'ix_car_images_sha256' not in existing_idxs:
            batch_op.create_index(batch_op.f('ix_car_images_sha256'), ['sha256'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('car_images', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_car_images_sha256'))
        batch_op.drop_index(batch_op.f('ix_car_images_phash'))
        batch_op.drop_column('fetched_at')
        batch_op.drop_column('image_blob')
        batch_op.drop_column('source_id')
        batch_op.drop_column('source_name')
        batch_op.drop_column('match_level')
        batch_op.drop_column('caption')
        batch_op.drop_column('shot_type')
        batch_op.drop_column('sort_order')
        batch_op.drop_column('is_active')
        batch_op.drop_column('is_hero')
        batch_op.drop_column('file_size')
        batch_op.drop_column('height')
        batch_op.drop_column('width')
        batch_op.drop_column('phash')
        batch_op.drop_column('sha256')

    with op.batch_alter_table('car_models', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_car_models_sha256'))
        batch_op.drop_index(batch_op.f('ix_car_models_car_id'))

    op.drop_table('car_models')
    with op.batch_alter_table('asset_fetch_log', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_asset_fetch_log_car_slug'))

    op.drop_table('asset_fetch_log')
    # ### end Alembic commands ###
