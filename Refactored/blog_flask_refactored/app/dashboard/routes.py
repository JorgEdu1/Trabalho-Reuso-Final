from flask import Blueprint, render_template, request, redirect, flash, url_for, current_app, abort
from app.extensions import db
from app.models.user import Blog_User
from app.models.posts import Blog_Posts
from app.dashboard.forms import The_Posts
# from app.dashboard.helpers import check_blog_picture, delete_blog_img
from app.models.themes import Blog_Theme
from app.models.helpers import update_stats_users_active, update_approved_post_stats, change_authorship_of_all_post
# from app.models.likes import Blog_Likes
# from app.models.bookmarks import Blog_Bookmarks
from app.models.comments import Blog_Comments, Blog_Replies
# from app.models.helpers import update_likes, update_bookmarks, delete_comment, delete_reply
# from datetime import datetime
from flask_login import login_required, current_user
# from werkzeug.utils import secure_filename
import os
from app.services.post_service import PostService
from app.services.user_service import UserService
from app.repositories.post_repository import PostRepository

dashboard = Blueprint('dashboard', __name__)

# Pages: dashboard, etc
# Routes available for all registered users of types admin and author

# ***********************************************************************************************
# USER MANAGEMENT: admin access only
# Managing users: see all users
@dashboard.route("/dashboard/manage_users", methods=["GET", "POST"])
@login_required
def users_table():
    user_type = current_user.type
    if user_type == "admin" or user_type == "super_admin":
        all_blog_users = Blog_User.query.order_by(Blog_User.id)
        return render_template("dashboard/users_table.html", logged_in=current_user.is_authenticated, all_blog_users=all_blog_users)
    else:
        flash("Access denied: admin access only.")
        return redirect(url_for('website.home'))

# Helper Method (Extraído via Extract Method)
def _perform_user_update_logic(user_to_update, form):
    """
    Função auxiliar que contém apenas a lógica de atualização e bloqueio.
    Reduz a complexidade da rota principal.
    """
    # Atualiza campos básicos
    user_to_update.name = form.get("username_update")
    user_to_update.email = form.get("email_update")
    user_to_update.type = form.get("accttype_update")
    user_to_update.blocked = form.get("acctblocked_update")

    # Lógica de bloqueio em Cascata (Comentários e Respostas)
    should_block = (form.get("acctblocked_update") == "TRUE")
    
    # Busca todos os comentários/respostas do usuário de uma vez
    user_comments = Blog_Comments.query.filter(Blog_Comments.user_id == user_to_update.id).all()
    user_replies = Blog_Replies.query.filter(Blog_Replies.user_id == user_to_update.id).all()
    
    # Aplica o estado (Bloqueado ou Desbloqueado)
    new_status = "TRUE" if should_block else "FALSE"
    
    for comment in user_comments:
        comment.blocked = new_status
    for reply in user_replies:
        reply.blocked = new_status

    db.session.commit()

# Managing users: update user
# REFATORADO - Extract Method aplicado para separar validação de lógica
@dashboard.route("/dashboard/manage_users/update/<int:id>", methods=["GET", "POST"])
@login_required
def user_update(id):
    acct_types = ["admin", "author", "user"]
    acct_blocked = ["FALSE", "TRUE"]
    user_to_update = Blog_User.query.get_or_404(id)

    if request.method == "POST":
        # Validação: Verifica duplicidade de Email
        if Blog_User.query.filter(Blog_User.id != id, Blog_User.email == request.form.get("email_update")).first():
            flash("This email is already registered with us.")
            return render_template("dashboard/users_user_update.html", id=user_to_update.id, logged_in=current_user.is_authenticated, user_to_update=user_to_update, acct_types=acct_types, acct_blocked=acct_blocked)
        
        # Validação: Verifica duplicidade de Username
        elif Blog_User.query.filter(Blog_User.id != id, Blog_User.name == request.form.get("username_update")).first():
            flash("This username is already registered with us.")
            return render_template("dashboard/users_user_update.html", id=user_to_update.id, logged_in=current_user.is_authenticated, user_to_update=user_to_update, acct_types=acct_types, acct_blocked=acct_blocked)
        
        else:
            # Regra de Negócio: Se mudar de autor para outro tipo, transfere posts
            if user_to_update.type == "author" and request.form.get("accttype_update") != "author":
                change_authorship_of_all_post(user_to_update.id, 2)

            # Executa a atualização (Chamada ao método extraído)
            try:
                _perform_user_update_logic(user_to_update, request.form)
                flash("User updated successfully!")
                return redirect(url_for('dashboard.users_table'))
            except Exception:
                db.session.rollback()
                flash("Error, try again.")
                return render_template("dashboard/users_user_update.html", id=user_to_update.id, logged_in=current_user.is_authenticated, user_to_update=user_to_update, acct_types=acct_types, acct_blocked=acct_blocked)
    else:
        return render_template("dashboard/users_user_update.html", logged_in=current_user.is_authenticated, user_to_update=user_to_update, acct_types=acct_types, acct_blocked=acct_blocked)

# Deleting user
# REFATORADO - Lógica movida para UserService
@dashboard.route("/dashboard/manage_users/delete/<int:id>", methods=["GET", "POST"])
@login_required
def user_delete(id):
    user_to_delete = Blog_User.query.get_or_404(id)
    
    if request.method == "POST":
        success, message = UserService.delete_user_cascade(id)
        
        if success:
            flash(message)
            return redirect(url_for('dashboard.users_table'))
        else:
            flash(message)
            if "Authorization" in message:
                 return render_template("dashboard/users_user_delete.html", logged_in=current_user.is_authenticated, user_to_delete=user_to_delete)
            
            return render_template("dashboard/users_user_delete.html", logged_in=current_user.is_authenticated, user_to_delete=user_to_delete)
            
    else:
        return render_template("dashboard/users_user_delete.html", logged_in=current_user.is_authenticated, user_to_delete=user_to_delete)

# Blocking user
# Blocking a user will not influence the stats of total active users.
# Blocked users will not be able to log in
@dashboard.route("/dashboard/manage_users/block/<int:id>", methods=["GET", "POST"])
@login_required
def user_block(id):
    user_to_block = Blog_User.query.get_or_404(id)
    if request.method == "POST":
        if id == 1:
            flash("Authorization error: this user cannot be blocked")
        else:
            user_to_block.blocked = "TRUE"
            # all comments and replies shall be blocked
            user_comments = Blog_Comments.query.filter(
                Blog_Comments.user_id == user_to_block.id).all()
            user_replies = Blog_Replies.query.filter(
                Blog_Replies.user_id == user_to_block.id).all()
            if user_comments:
                for comment in user_comments:
                    comment.blocked = "TRUE"
            if user_replies:
                for reply in user_replies:
                    reply.blocked = "TRUE"
            try:
                db.session.commit()
                flash("User blocked successfully.")
                return redirect(url_for('dashboard.users_table'))
            except:
                db.session.rollback()
                flash("There was a problem blocking this user.")
                return render_template("dashboard/users_user_block.html", logged_in=current_user.is_authenticated, user_to_block=user_to_block)
    else:
        return render_template("dashboard/users_user_block.html", logged_in=current_user.is_authenticated, user_to_block=user_to_block)

# Previewing a user's account information
@dashboard.route("/dashboard/manage_users/preview/<int:id>")
@login_required
def user_preview(id):
    user_to_preview = Blog_User.query.get_or_404(id)
    return render_template("dashboard/users_user_preview.html", logged_in=current_user.is_authenticated, user_to_preview=user_to_preview)

# ***********************************************************************************************
# POST MANGEMENT

# ADDING NEW BLOG POST -  AUTHORS ONLY
# Only users of type authors can add new posts
@dashboard.route("/dashboard/submit_new_post", methods=["GET", "POST"])
@login_required
def submit_post():
    from app.extensions import db # Apenas para popular o SelectField se necessário, ou crie ThemeRepository
    themes_list = [(u.id, u.theme) for u in db.session.query(Blog_Theme).all()]
    
    form = The_Posts()
    form.theme.choices = themes_list

    if form.validate_on_submit():
        try:
            PostService.create_post(form, current_user.id)
            flash("Blog post submitted successfully!", "success")
            return redirect(url_for('account.dashboard'))
        except Exception as e:
            flash(f"Error saving post: {str(e)}", "danger")

    return render_template("dashboard/posts_submit_new.html", logged_in=current_user.is_authenticated, form=form)

# POST MANGEMENT -  ADMIN
# View table with all posts and manage posts: Admin only
@dashboard.route("/dashboard/manage_posts")
@login_required
def posts_table():
    all_blog_posts_submitted = Blog_Posts.query.order_by(Blog_Posts.id)
    return render_template("dashboard/posts_table.html", logged_in=current_user.is_authenticated, all_blog_posts_submitted=all_blog_posts_submitted)

# Approve posts: only users of type admin can approve posts
# Approved posts are published on the blog
# When a post is approved, this will count towards active posts in the blog statictics.

@dashboard.route("/dashboard/manage_posts/approve_post/<int:id>", methods=["GET", "POST"])
@login_required
def approve_post(id):
    post_to_approve = Blog_Posts.query.get_or_404(id)
    if request.method == "POST":
        post_to_approve.admin_approved = "TRUE"
        try:
            db.session.commit()
            flash("This post has been admin approved.")
            update_approved_post_stats(1)
            return redirect(url_for('dashboard.posts_table'))
        except:
            flash("There was a problem approving this post.")
            return render_template("dashboard/posts_approve_post.html", logged_in=current_user.is_authenticated, post_to_approve=post_to_approve)
    else:
        return render_template("dashboard/posts_approve_post.html", logged_in=current_user.is_authenticated, post_to_approve=post_to_approve)

# Disapprove (disallow) posts: only user accounts of type admin can disapprove a post
# Disapproving a post will unpublish it from the blog
# This action will be reflected in the blog stats of active posts
@dashboard.route("/dashboard/manage_posts/disallow_post/<int:id>", methods=["GET", "POST"])
@login_required
def disallow_post(id):
    post_to_disallow = Blog_Posts.query.get_or_404(id)
    if request.method == "POST":
        post_to_disallow.admin_approved = "FALSE"
        try:
            db.session.commit()
            flash("This post is no longer admin approved.")
            update_approved_post_stats(-1)
            return redirect(url_for('dashboard.posts_table'))
        except:
            flash("There was a problem disallowing this post.")
            return render_template("dashboard/posts_disallow_post.html", logged_in=current_user.is_authenticated, post_to_disallow=post_to_disallow)
    else:
        return render_template("dashboard/posts_disallow_post.html", logged_in=current_user.is_authenticated, post_to_disallow=post_to_disallow)

# POST MANAGEMENT - AUTHORS DASH
# View table with all posts this author has submitted
@dashboard.route("/dashboard/manage_posts_author")
@login_required
def posts_table_author():
    all_blog_posts_submitted = Blog_Posts.query.filter(
        Blog_Posts.author_id == current_user.id).all()
    return render_template("dashboard/posts_table_author.html", logged_in=current_user.is_authenticated, all_blog_posts_submitted=all_blog_posts_submitted)


# POST MANGEMENT -  ADMIN AND AUTHORS
# Previewing a post
@dashboard.route("/dashboard/manage_posts_author/preview_post/<int:id>", endpoint='preview_post_author')
@dashboard.route("/dashboard/manage_posts/preview_post/<int:id>")
@login_required
def preview_post(id):
    post_to_preview = Blog_Posts.query.get_or_404(id)
    return render_template("dashboard/posts_preview_post.html", logged_in=current_user.is_authenticated, post_to_preview=post_to_preview)

# Editing a post - ADMIN AND AUTHORS
@dashboard.route("/dashboard/manage_posts_author/edit_post/<int:id>", endpoint='edit_post_author', methods=["GET", "POST"])
@dashboard.route("/dashboard/manage_posts/edit_post/<int:id>", methods=["GET", "POST"])
@login_required
def edit_post(id):
    from app.repositories.post_repository import PostRepository
    from app.models.themes import Blog_Theme
    from app.extensions import db # Apenas para query de leitura rápida dos temas
    
    post = PostRepository.get_by_id(id)
    
    if current_user.type != "admin" and current_user.type != "super_admin" and post.author_id != current_user.id:
        abort(403)

    form = The_Posts()
    
    themes_list = [(u.id, u.theme) for u in db.session.query(Blog_Theme).all()]
    form.theme.choices = themes_list

    if form.validate_on_submit():
        try:
            PostService.update_post(id, form)
            flash("Post editado com sucesso!", "success")
            
            if current_user.type in ["admin", "super_admin"]:
                return redirect(url_for("dashboard.posts_table"))
            else:
                return redirect(url_for("dashboard.posts_table_author"))
        except Exception as e:
            flash(f"Erro ao atualizar post: {str(e)}", "danger")

    elif request.method == 'GET':
        form.process(obj=post)

    return render_template('dashboard/posts_edit_post.html', 
                           logged_in=current_user.is_authenticated, 
                           form=form, 
                           post_to_edit=post)

# Deleting a post 
@dashboard.route("/dashboard/manage_posts_author/delete_post/<int:id>", endpoint='delete_post_author', methods=["GET", "POST"])
@dashboard.route("/dashboard/manage_posts/delete_post/<int:id>", methods=["GET", "POST"])
@login_required
def delete_post(id):
    post = PostRepository.get_by_id(id)
    
    if request.method == "GET":
        return render_template("dashboard/posts_delete_post.html", 
                               logged_in=current_user.is_authenticated, 
                               post_to_delete=post,
                               post_likes=[], comments=[]) 

    try:
        PostService.delete_post(id)
        flash("Post deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting post: {str(e)}", "danger")

    if current_user.type == "author":
        return redirect(url_for('dashboard.posts_table_author'))
    else:
        return redirect(url_for('dashboard.posts_table'))