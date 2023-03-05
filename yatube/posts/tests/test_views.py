from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.core.cache import cache
from django.conf import settings
import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from posts.models import Post, Group, Comment, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.user = User.objects.create_user(username='author')
        cls.user_follow = User.objects.create(username='FollowUser')
        cls.group = Group.objects.create(
            description='Тестовый заголовок',
            title='Тестовый титл',
            slug='test-slug',
        )
        cls.other_group = Group.objects.create(
            description='Другой тестовый заголовок',
            title='Другой тестовый титл',
            slug='test-other-slug',
        )
        cls.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.uploaded = SimpleUploadedFile(
            name="small.gif", content=cls.small_gif, content_type="image/gif"
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text="Тестовый комментарий",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_other = Client()
        self.authorized_client_other.force_login(self.user_follow)
        cache.clear()

    def check_the_object_context_matches(self, post):
        self.assertIsInstance(post, Post)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.id, self.post.id)
        self.assertEqual(post.image, self.post.image)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': (
                reverse('posts:group_list', kwargs={'slug': 'test-slug'})
            ),
            'posts/create_post.html': reverse('posts:post_create'),
            'posts/post_detail.html': (
                reverse('posts:post_detail', kwargs={'post_id': self.post.id})
            ),
            'posts/profile.html': (
                reverse(
                    'posts:profile', kwargs={'username': self.user.username}
                )
            )
        }

        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page(self):
        response = self.authorized_client.get(reverse('posts:index'))
        post = response.context.get('page_obj')[0]
        self.check_the_object_context_matches(post)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id}))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile равен ожидаемому контексту."""
        response = self.authorized_client.get(
            reverse("posts:profile", kwargs={"username": self.post.author})
        )
        post = response.context.get('page_obj')[0]
        self.assertEqual(response.context.get('author'), self.post.author)
        self.check_the_object_context_matches(post)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        post = response.context.get('page_obj')[0]
        self.check_the_object_context_matches(post)
        self.assertEqual(response.context.get('group'), self.group)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})))
        post = response.context.get('post')
        self.check_the_object_context_matches(post)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный Пост с группой не попап в чужую группу."""
        response = self.authorized_client.get(
            reverse(
                "posts:group_list", kwargs={"slug": self.other_group.slug}
            )
        )
        self.assertEqual(len(response.context.get('page_obj')), 0)

    def test_comment(self):
        """Проверка появления коммента и валидности формы"""
        comments_count = Comment.objects.count()
        text_com = "Тестовый комментарий"
        form_data = {"text": text_com}
        response = self.guest_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, f"/auth/login/?next=/posts/{self.post.pk}/comment/"
        )
        self.assertNotEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(text=text_com).exists()
        )

    def test_cache(self):
        """Проверка работоспособности кэша"""
        Post.objects.create(author=self.user, text='test_cache')
        response_1 = self.guest_client.get(reverse('posts:index'))
        Post.objects.all().delete()
        response_2 = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response_2.content, response_3.content)

    def test_image_in_post_detail_page(self):
        """Картинка передается на страницу post_detail."""
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        obj = response.context["post"]
        self.assertEqual(obj.image, self.post.image)

    def test_following(self):
        """Проверка работоспособности подписок"""
        response = self.authorized_client.get(reverse(
            'posts:profile_follow', args=(self.user_follow,)))
        self.assertRedirects(response, reverse(
            'posts:profile', args=(self.user_follow,)))
        self.assertEqual(Follow.objects.count(), 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user, author=self.user_follow
            ).exists()
        )

    def test_unfollowing(self):
        """Проверка работоспособности отписок"""
        Follow.objects.create(user=self.user_follow, author=self.user)
        response = self.authorized_client_other.get(reverse(
            'posts:profile_unfollow', args=(self.user,)))
        self.assertRedirects(response, reverse(
            'posts:profile', args=(self.user,)))
        self.assertEqual(Follow.objects.count(), 0)

    def test_follower_have_post(self):
        """У подписчика отображаются посты автора"""
        Follow.objects.create(user=self.user_follow, author=self.user)
        response = self.authorized_client_other.get(reverse(
            'posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 1)
        post = response.context.get('page_obj')[0]
        self.check_the_object_context_matches(post)

    def test_unfollower_have_not_post(self):
        response = self.authorized_client_other.get(
            reverse("posts:follow_index")
        )
        self.assertNotIn(self.post, response.context["page_obj"])


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            description='Тестовый заголовок',
            title='Тестовый титл',
            slug='test-slug',
        )

    def setUp(self):
        self.user = User.objects.create_user(username='StasBasov')

    def test_paginator(self):
        """Пагинатор корректно разбивает и выводит записи постранично"""
        cache.clear()
        posts = [Post(text=f'Тестовый текст {i}',
                      group=self.group,
                      author=self.user) for i in range(13)]
        Post.objects.bulk_create(posts)
        paginator_address = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for paginator in paginator_address:
            with self.subTest(paginator=paginator):
                response = self.client.get(paginator)
                self.assertEqual(len(response.context['page_obj']), 10)
                response = self.client.get(paginator + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)
