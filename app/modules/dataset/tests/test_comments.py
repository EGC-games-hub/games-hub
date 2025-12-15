import pytest

from flask_login import login_user
from werkzeug.exceptions import HTTPException

from app import db
from app.modules.auth.repositories import UserRepository
from app.modules.dataset.comment_service import CommentService
from app.modules.dataset.models import DatasetComment, PublicationType
from app.modules.dataset.repositories import DSMetaDataRepository, DataSetRepository
from app.modules.dataset.routes import moderate_comment


@pytest.fixture
def create_user():
    def _create(email="user@example.com", password="pass", role=None):
        repo = UserRepository()
        if role:
            return repo.create(email=email, password=password, role=role)
        return repo.create(email=email, password=password)

    return _create


def create_dataset_for_user(user):
    dsmeta_repo = DSMetaDataRepository()
    dataset_repo = DataSetRepository()

    dsmeta = dsmeta_repo.create(title="T", description="D", publication_type=PublicationType.NONE)
    dataset = dataset_repo.create(user_id=user.id, ds_meta_data_id=dsmeta.id)
    return dataset


def test_comment_service_crud(clean_database, create_user):
    author = create_user(email="author@example.com", password="pass")

    dataset = create_dataset_for_user(author)

    service = CommentService()

    # Create
    comment = service.create(dataset=dataset, user=author, content="Hello world")
    assert comment.id is not None
    assert comment.content == "Hello world"

    # List and get
    listed = service.list_for_dataset(dataset)
    assert any(c.id == comment.id for c in listed)

    fetched = service.get(comment.id)
    assert fetched is not None and fetched.content == "Hello world"

    # Delete
    service.delete(fetched)
    assert service.get(comment.id) is None


def test_list_visibility_filter(clean_database, create_user):
    author = create_user(email="author2@example.com", password="pass")
    dataset = create_dataset_for_user(author)
    service = CommentService()

    visible = service.create(dataset=dataset, user=author, content="Visible comment")

    # create a hidden comment directly
    hidden = DatasetComment(dataset_id=dataset.id, user_id=author.id, content="Hidden", is_visible=False)
    db.session.add(hidden)
    db.session.commit()

    visible_list = service.list_for_dataset(dataset)
    assert any(c.id == visible.id for c in visible_list)
    assert all(c.is_visible for c in visible_list)

    all_list = service.list_for_dataset(dataset, include_hidden=True)
    ids = [c.id for c in all_list]
    assert visible.id in ids and hidden.id in ids


def test_moderate_comment_permissions(test_client, clean_database, create_user):
    # users
    author = create_user(email="author3@example.com", password="pass")
    other = create_user(email="other@example.com", password="pass")
    admin = create_user(email="admin@example.com", password="pass", role="admin")

    dataset = create_dataset_for_user(author)

    # create comment
    comment = DatasetComment(dataset_id=dataset.id, user_id=author.id, content="To be moderated")
    db.session.add(comment)
    db.session.commit()

    # other user should get 403
    with test_client.application.test_request_context(f"/dataset/{dataset.id}/comments/{comment.id}/moderate", method="POST", data={"action": "delete"}):
        login_user(other)
        with pytest.raises(Exception) as exc:
            moderate_comment(dataset.id, comment.id)
        assert getattr(exc.value, "code", None) == 403

    # author can delete
    # recreate comment
    comment2 = DatasetComment(dataset_id=dataset.id, user_id=author.id, content="Author delete")
    db.session.add(comment2)
    db.session.commit()

    with test_client.application.test_request_context(f"/dataset/{dataset.id}/comments/{comment2.id}/moderate", method="POST", data={"action": "delete"}):
        login_user(author)
        resp = moderate_comment(dataset.id, comment2.id)

    assert DatasetComment.query.get(comment2.id) is None

    # admin can delete
    comment3 = DatasetComment(dataset_id=dataset.id, user_id=author.id, content="Admin delete")
    db.session.add(comment3)
    db.session.commit()

    with test_client.application.test_request_context(f"/dataset/{dataset.id}/comments/{comment3.id}/moderate", method="POST", data={"action": "delete"}):
        login_user(admin)
        resp = moderate_comment(dataset.id, comment3.id)

    assert DatasetComment.query.get(comment3.id) is None
