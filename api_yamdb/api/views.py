from django.core.mail import send_mail
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from api.mixins import CreateUpdateDeleteViewSet
from api.permissions import (
    AuthorOrAdminOrModeratOrReadOnly,
    IsAdminOrReadOnly,
    IsAdminRole,
    IsAuthenticatedOrCreateOnly,
)
from api.serializers import (
    CategorySerializer,
    CommentSerializer,
    GenreSerializer,
    ReviewSerializer,
    SignUpSerializer,
    TitleOnlyReadSerializer,
    TitleSerializer,
    TokenSerializer,
    UserMeSerializer,
    UserSerializer,
)
from reviews.models import Category, Genre, Review, Title
from users.models import User

from .filters import TitleFilter
from .utils import check_confirmation_code

ALLOWED_METHODS = ("get", "post", "patch", "delete")


class ListCreateDestroyViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass


class CategoryViewSet(CreateUpdateDeleteViewSet):
    """Вьюсет модели категорий."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]
    filter_backends = [filters.SearchFilter]
    lookup_field = "slug"
    search_fields = ("name",)
    pagination_class = PageNumberPagination

    @action(
        detail=False,
        methods=["delete"],
        url_path=r"(?P<slug>\w+)",
        lookup_field="slug",
        url_name="category_slug",
    )
    def delete_category(self, request, slug):
        category = self.get_object()
        serializer = CategorySerializer(category)
        category.delete()
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)


class GenreViewSet(CreateUpdateDeleteViewSet):
    """Вьюсет модели жанров."""

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]
    filter_backends = [filters.SearchFilter]
    lookup_field = "slug"
    search_fields = ("name",)
    pagination_class = PageNumberPagination

    @action(
        detail=False,
        methods=["delete"],
        url_path=r"(?P<slug>\w+)",
        lookup_field="slug",
        url_name="category_slug",
    )
    def delete_genre(self, request, slug):
        category = self.get_object()
        serializer = CategorySerializer(category)
        category.delete()
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)


class TitleViewSet(viewsets.ModelViewSet):
    """Вьюсет модели произведений."""

    queryset = (
        Title.objects.annotate(rating=Avg("reviews__score"))
        .select_related("category")
        .prefetch_related("genre")
    )
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = TitleFilter
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TitleOnlyReadSerializer
        return TitleSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    """Вьюсет модели ревью на произведение."""

    pagination_class = PageNumberPagination
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        AuthorOrAdminOrModeratOrReadOnly,
    )
    serializer_class = ReviewSerializer

    def get_queryset(self):
        title_id = self.kwargs.get("title_id")
        title = get_object_or_404(Title, id=title_id)
        return title.reviews.select_related("author")

    def perform_create(self, serializer):
        title_id = self.kwargs.get("title_id")
        title = get_object_or_404(Title, id=title_id)
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    """Вьюсет модели комментария к ревью на произведение."""

    permission_classes = (
        IsAuthenticatedOrCreateOnly,
        AuthorOrAdminOrModeratOrReadOnly,
    )
    pagination_class = PageNumberPagination
    serializer_class = CommentSerializer

    def get_review(self):
        review_id = self.kwargs.get("review_id")
        return get_object_or_404(Review, id=review_id)

    def get_queryset(self):
        return self.get_review().comments.select_related("author")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, review=self.get_review())


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет модели юзера."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [
        filters.SearchFilter,
    ]
    search_fields = [
        "username",
    ]
    lookup_field = "username"
    permission_classes = [
        IsAuthenticated,
        IsAdminRole,
    ]
    pagination_class = PageNumberPagination
    http_method_names = ALLOWED_METHODS

    @action(
        methods=["GET", "PATCH"],
        detail=False,
        permission_classes=(IsAuthenticated,),
        url_path="me",
    )
    def me(self, request):
        serializer = UserSerializer(request.user)
        if request.method == "PATCH":
            if request.user.is_admin:
                serializer = UserMeSerializer(
                    request.user, data=request.data, partial=True
                )
            else:
                serializer = UserSerializer(
                    request.user, data=request.data, partial=True
                )
            serializer.is_valid(raise_exception=True)
            serializer.save(role=request.user.role, partial=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SignUpViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Вьюсет для регистрации."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = SignUpSerializer

    def create(self, request):
        serializer = SignUpSerializer(data=request.data)
        if User.objects.filter(
            username=request.data.get("username"),
            email=request.data.get("email"),
        ):
            user = User.objects.get(username=request.data.get("username"))
            serializer = SignUpSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            username = request.data.get("username")
            user = User.objects.get(username=username)
            code = user.confirmation_code
            send_mail(
                f"Добро пожаловать в YaMDb, {user.username}!",
                (f"Ваш confirmation_code: {code} "),
                None,
                [request.data.get("email")],
                fail_silently=False,
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Token(APIView):
    """Вьюсет для получения токена."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirmation_code = serializer.validated_data.get("confirmation_code")
        username = serializer.validated_data.get("username")
        user = get_object_or_404(User, username=username)
        if check_confirmation_code(user, confirmation_code):
            token = AccessToken.for_user(user)
            return Response({"token": f"{token}"}, status=status.HTTP_200_OK)
        return Response(
            {"confirmation_code": ["Код не действителен!"]},
            status=status.HTTP_400_BAD_REQUEST,
        )
