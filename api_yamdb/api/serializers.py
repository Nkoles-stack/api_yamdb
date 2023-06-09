import datetime as dt

from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from reviews.models import Category, Comment, Genre, Review, Title
from users.models import User


class CategorySerializer(serializers.ModelSerializer):
    """Cериалайзер для категорий."""

    class Meta:
        model = Category
        fields = ("name", "slug")
        lookup_field = "slug"


class GenreSerializer(serializers.ModelSerializer):
    """Cериалайзер для жанров."""

    class Meta:
        model = Genre
        fields = ("name", "slug")
        lookup_field = "slug"


class TitleSerializer(serializers.ModelSerializer):
    """Cериалайзер для произведений."""

    year = serializers.IntegerField()
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), many=False
    )
    genre = serializers.SlugRelatedField(
        slug_field="slug", many=True, queryset=Genre.objects.all()
    )

    class Meta:
        model = Title
        fields = (
            "id",
            "name",
            "year",
            "description",
            "genre",
            "category",
        )

    def validate_year(self, data):
        if data >= dt.datetime.now().year and data < 0:
            raise serializers.ValidationError(
                "Введите корректный год!",
            )
        return data

    def to_representation(self, title):
        serializer = TitleOnlyReadSerializer(title)
        return serializer.data


class TitleOnlyReadSerializer(serializers.ModelSerializer):
    """Cериалайзер для получения списка произведений."""

    rating = serializers.IntegerField(
        read_only=True,
    )
    category = CategorySerializer(read_only=True)
    genre = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Title
        fields = (
            "id",
            "name",
            "year",
            "rating",
            "description",
            "genre",
            "category",
        )
        read_only_fields = (
            "id",
            "name",
            "year",
            "rating",
            "description",
            "genre",
            "category",
        )


class CommentSerializer(serializers.ModelSerializer):
    """Сериализатор модели комментария к ревью."""

    author = serializers.SlugRelatedField(
        read_only=True,
        slug_field="username",
    )

    class Meta:
        fields = (
            "id",
            "author",
            "text",
            "pub_date",
        )
        model = Comment
        read_only_fields = ("review",)


class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор модели ревью на произведение."""

    title = serializers.SlugRelatedField(
        slug_field="id", queryset=Title.objects.all(), required=False
    )
    score = serializers.IntegerField()
    author = serializers.SlugRelatedField(
        slug_field="username",
        read_only=True,
        default=serializers.CurrentUserDefault(),
    )

    comments = CommentSerializer(many=True, required=False, read_only=True)

    class Meta:
        fields = (
            "id",
            "text",
            "pub_date",
            "author",
            "title",
            "score",
            "comments",
        )
        read_only_fields = (
            "id",
            "pub_date",
            "author",
        )
        model = Review

    def validate(self, data):
        if self.context.get("request").method != "POST":
            return data
        author = self.context.get("request").user
        title_id = self.context.get("view").kwargs.get("title_id")
        if Review.objects.filter(author=author, title=title_id).exists():
            raise serializers.ValidationError(
                "Нельзя оставлять повторный отзыв."
            )
        return data

    def validate_score(self, score):
        if not (1 <= score <= 10):
            raise serializers.ValidationError("Проверьте оценку!")
        return score


class UserSerializer(serializers.ModelSerializer):
    """Cериалайзер для юзеров."""

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "role",
            "first_name",
            "last_name",
            "bio",
        )

    def validate_username(self, value):
        if value == "me":
            raise serializers.ValidationError(
                "Нельзя использовать me в качестве username"
            )
        return value


class SignUpSerializer(serializers.ModelSerializer):
    """Cериалайзер для регистрации новых юзеров."""

    class Meta:
        model = User
        fields = ("email", "username")

    def validate_username(self, value):
        if value == "me":
            raise serializers.ValidationError(
                "Нельзя использовать me в качестве username"
            )
        return value


class UserMeSerializer(UserSerializer):
    """Cериалайзер для получения информации о юзере."""

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "role",
            "first_name",
            "last_name",
            "bio",
        )
        read_only_fields = ("role",)


class TokenSerializer(serializers.Serializer):
    """Cериалайзер для получения токена."""

    username = serializers.CharField(
        required=True,
        max_length=150,
        validators=[
            UnicodeUsernameValidator,
        ],
    )
    confirmation_code = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ("username", "confirmation_code")
