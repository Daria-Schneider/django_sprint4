from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import CommentForm, PostForm, UserProfileForm, UserRegistrationForm
from .models import Category, Comment, Post


User = get_user_model()


def _visible_posts_queryset():
    return (
        Post.objects.select_related('category', 'author')
        .filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        )
    )


def _can_view_post(user, post):
    if user.is_authenticated and post.author == user:
        return True
    return (
        post.is_published
        and post.pub_date <= timezone.now()
        and post.category is not None
        and post.category.is_published
    )


def _paginate(request, queryset):
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    template = 'blog/index.html'
    page_obj = _paginate(request, _visible_posts_queryset().order_by('-pub_date'))
    return render(request, template, context={'page_obj': page_obj})


def category_posts(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug, is_published=True)
    queryset = _visible_posts_queryset().filter(category=category).order_by('-pub_date')
    page_obj = _paginate(request, queryset)
    return render(request, 'blog/category.html', context={'category': category, 'page_obj': page_obj})


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    if request.user.is_authenticated and request.user == profile_user:
        queryset = (
            Post.objects.select_related('category', 'author')
            .filter(author=profile_user)
            .order_by('-pub_date')
        )
    else:
        queryset = (
            _visible_posts_queryset()
            .filter(author=profile_user)
            .order_by('-pub_date')
        )
    page_obj = _paginate(request, queryset)
    return render(
        request,
        'blog/profile.html',
        context={'profile': profile_user, 'page_obj': page_obj},
    )


@login_required
def edit_profile(request):
    profile_user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile_user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', profile_user.username)
    else:
        form = UserProfileForm(instance=profile_user)
    return render(request, 'blog/user.html', {'form': form})


def post_detail(request, id):
    post = get_object_or_404(Post.objects.select_related('category', 'author'), pk=id)
    if not _can_view_post(request.user, post):
        raise Http404
    comments = post.comments.select_related('author').order_by('created_at')
    form = CommentForm()
    return render(
        request,
        'blog/detail.html',
        {'post': post, 'comments': comments, 'form': form},
    )


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', request.user.username)
    else:
        form = PostForm()
    return render(request, 'blog/create.html', {'form': form})


@login_required
def post_edit(request, id):
    post = get_object_or_404(Post, pk=id)
    if request.user != post.author:
        return redirect('blog:post_detail', id=post.id)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', id=post.id)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def post_delete(request, id):
    post = get_object_or_404(Post, pk=id)
    if request.user != post.author:
        return redirect('blog:post_detail', id=post.id)
    if request.method == 'POST':
        username = post.author.username
        post.delete()
        return redirect('blog:profile', username)
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, id):
    post = get_object_or_404(Post.objects.select_related('category', 'author'), pk=id)
    if not _can_view_post(request.user, post):
        raise Http404
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect('blog:post_detail', id=post.id)
    else:
        form = CommentForm()
    comments = post.comments.select_related('author').order_by('created_at')
    return render(request, 'blog/detail.html', {'post': post, 'comments': comments, 'form': form})


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', id=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', id=post_id)
    else:
        form = CommentForm(instance=comment)
    return render(request, 'blog/comment.html', {'form': form, 'comment': comment})


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})


def registration(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('blog:profile', user.username)
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/registration_form.html', {'form': form})
