from posts.models import Post, Group, User
from django.test import Client, TestCase
from django.urls import reverse


class PostFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="NoName")
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в post_create."""
        # Подсчитаем количество записей в post_create
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем перенаправление на профиль
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={"username": self.user.username})
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст'
            ).exists()
        )

    def test_edit_post(self):
        """Проверка редактирования записи в post_edit"""
        self.post = Post.objects.create(
            author=self.user,
            text="Тестовый текст",
        )
        self.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        posts_count = Post.objects.count()
        form_data = {"text": "Изменяем текст", "group": self.group.id}
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                "posts:post_detail", kwargs={"post_id": self.post.id}
            )
        )
        # Проверяем изменилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(text="Изменяем текст").exists())
