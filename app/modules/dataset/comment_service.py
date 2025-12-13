from datetime import datetime
from typing import List, Optional

from flask_login import current_user

from app import db
from app.modules.dataset.models import DatasetComment, DataSet
from app.modules.auth.models import User


class CommentService:
    def create(self, dataset: DataSet, user: User, content: str) -> DatasetComment:
        # Comments are visible immediately by default.
        comment = DatasetComment(
            dataset_id=dataset.id,
            user_id=user.id,
            content=content,
            created_at=datetime.utcnow(),
            is_visible=True,
        )
        db.session.add(comment)
        db.session.commit()
        return comment

    def list_for_dataset(self, dataset: DataSet, include_hidden: bool = False) -> List[DatasetComment]:
        query = DatasetComment.query.filter_by(dataset_id=dataset.id)
        if not include_hidden:
            query = query.filter_by(is_visible=True)
        return query.order_by(DatasetComment.created_at.asc()).all()

    def get(self, comment_id: int) -> Optional[DatasetComment]:
        return DatasetComment.query.get(comment_id)

    def approve(self, comment: DatasetComment):
        comment.is_visible = True
        db.session.add(comment)
        db.session.commit()
        return comment

    def delete(self, comment: DatasetComment):
        db.session.delete(comment)
        db.session.commit()


# Helper to decide if a user is admin. Project doesn't have a standard admin flag everywhere,
# so keep a permissive check that looks for common attributes.

def is_admin(user) -> bool:
    if not user:
        return False
    # common patterns
    if hasattr(user, "is_admin") and getattr(user, "is_admin"):
        return True
    # profile-based
    if hasattr(user, "profile") and getattr(user.profile, "is_admin", False):
        return True
    return False
