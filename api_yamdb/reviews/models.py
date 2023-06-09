from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    validate_slug,
)
from django.db import models

from users.models import User

from .validators import validate_year


class Category(models.Model):
    """Модель для категорий."""

    name = models.CharField(
        "Название",
        max_length=256,
    )
    slug = models.SlugField(
        "Slug",
        max_length=50,
        unique=True,
        validators=[validate_slug],
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        default_related_name = "categories"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Genre(models.Model):
    """Модель для жанров."""

    slug = models.SlugField(
        "Slug",
        max_length=50,
        unique=True,
        validators=[validate_slug],
    )
    name = models.CharField(
        "Название",
        max_length=256,
    )

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"
        default_related_name = "genres"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Title(models.Model):
    """Модель для произведений."""

    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        on_delete=models.PROTECT,
        related_name="titles",
        db_index=True,
        blank=True,
        null=True,
    )
    description = models.TextField(
        "Описание",
        db_index=True,
        blank=True,
    )
    genre = models.ManyToManyField(
        Genre,
        verbose_name="Жанр",
        related_name="titles",
        blank=True,
        db_index=True,
    )
    name = models.CharField(
        "Название",
        max_length=256,
        db_index=True,
    )
    year = models.IntegerField(
        "Год выпуска", null=False, db_index=True, validators=[validate_year]
    )

    class Meta:
        verbose_name = "Произведение"
        verbose_name_plural = "Произведения"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.year is not None:
            validate_year(self.year)


class Review(models.Model):
    """Модель для отзывов."""

    title = models.ForeignKey(
        Title,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Произведение",
        db_index=True,
        null=False,
    )
    score = models.IntegerField(
        verbose_name="Рейтинг",
        db_index=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],
    )
    text = models.TextField("Текст ревью", null=False, blank=False)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор ревью",
    )
    pub_date = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-pub_date",)
        constraints = [
            models.UniqueConstraint(
                name="unique_title_author",
                fields=["title", "author"],
            ),
        ]
        default_related_name = "reviews"


class Comment(models.Model):
    """Модель для комментариев."""

    text = models.TextField("Текст комментария", null=False, blank=False)
    pub_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор комментария",
    )
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, verbose_name="Ревью"
    )

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        default_related_name = "comments"
