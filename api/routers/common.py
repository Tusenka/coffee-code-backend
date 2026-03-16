from db.user_repository import UserRepository
from db.notification_repository import NotificationRepository
from service.catalog_service import CatalogService
from service.cloudinary import CloudinaryService
from service.recommendation_service import RecommendationService
from service.user_service import UserService
from service.notification_service import NotificationService

user_repo = UserRepository()
photo_storage = CloudinaryService()
recommendation_service = RecommendationService()
user_service = UserService()
catalog_service = CatalogService()
notification_repo = NotificationRepository()
notification_service = NotificationService()
