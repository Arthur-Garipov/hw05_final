from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField('Текст поста', help_text='Текст нового поста')
    pub_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts'
    )

    def __str__(self):
        return self.post.text[:15]

    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='posts',
        help_text='Группа, к которой будет относится пост',
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ["-pub_date"]


class Comment(models.Model):
    post = models.ForeignKey(
        Post, blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="comments"
    )
    text = models.TextField(
        'Текст комментария',
        help_text="Введите текст комментария"
    )
    created = models.DateTimeField(
        "Дата публикации",
        auto_now_add=True
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.text


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
