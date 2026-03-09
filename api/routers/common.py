from db.user_repository import UserRepository
from service.catalog_service import CatalogService
from service.cloudinary import CloudinaryService
from service.recommendation_service import RecommendationService
from service.user_service import UserService

user_repo = UserRepository()
photo_storage = CloudinaryService()
recommendation_service = RecommendationService()
user_service = UserService()
catalog_service = CatalogService()
