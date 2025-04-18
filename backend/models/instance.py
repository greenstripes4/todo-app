# /config/workspace/todo-app/backend/models/instance.py
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid # Import the uuid module

class Instance(db.Model):
    __tablename__ = 'instance'

    # References _workflow.id and acts as PK
    id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow.id', ondelete='CASCADE'), primary_key=True)
    # Column name kept as 'bullshit' per schema, consider renaming for clarity
    bullshit = db.Column(db.Text, nullable=True)
    spec_name = db.Column(db.Text, nullable=True)
    active_tasks = db.Column(db.Integer, nullable=True)
    # Use timezone=True for TIMESTAMP WITH TIME ZONE in PostgreSQL
    started = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())
    ended = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationship (One-to-one)
    workflow = db.relationship('Workflow', back_populates='instance')

    def __repr__(self):
        return f'<Instance {self.id} Spec={self.spec_name}>'

