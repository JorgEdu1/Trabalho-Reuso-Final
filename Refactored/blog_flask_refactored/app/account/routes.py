from flask import Blueprint, render_template, request, redirect, flash, url_for, current_app
from app.extensions import db, login_manager
from app.models.user import Blog_User
from app.models.posts import Blog_Posts
from app.account.forms import The_Accounts
from app.models.stats import Blog_Stats
from app.models.bookmarks import Blog_Bookmarks
# from app.models.likes import Blog_Likes
from app.models.comments import Blog_Comments, Blog_Replies
# from app.account.helpers import hash_pw
# from app.models.helpers import  update_stats_users_total, update_stats_users_active, delete_comment, delete_reply, change_authorship_of_all_post, update_bookmarks, update_likes
# from app.general_helpers.helpers import check_image_filename
from flask_login import login_user, login_required, current_user, logout_user
# from werkzeug.security import check_password_hash  # used in login
# from werkzeug.utils import secure_filename
from sqlalchemy import desc
from datetime import datetime
import uuid as uuid
import os
from app.services.user_service import UserService

account = Blueprint('account', __name__)

# Pages: login, logout, signup, account
# Routes available for all registered users (all user types) + login and signup (available for all registered and non-registered users)

# ***********************************************************************************************
# LOGIN, SIGN UP, LOG OUT
@login_manager.user_loader
def load_user(user_id):
    return Blog_User.query.get(int(user_id))

@account.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user, status = UserService.signup_user(request.form)
        
        if status == "email_exists":
            flash("This email is already registered with us. Log-in instead!")
            return redirect(url_for("account.login"))
        
        if status == "success" and user:
            login_user(user)
            return redirect(url_for('account.dashboard'))

    return render_template('account/signup.html', logged_in=current_user.is_authenticated)

@account.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        
        user, status = UserService.login_user(email, password)
        
        if status == "email_not_found":
            flash("This email does not exist in our database.")
            return redirect(url_for("account.login"))
        elif status == "wrong_password":
            flash("Incorrect password, please try again.")
            return redirect(url_for("account.login"))
        elif status == "blocked":
            flash("Your account has been blocked. Please contact us for more information")
            return redirect(url_for("account.login"))
        elif status == "success":
            login_user(user)
            return redirect(url_for('account.dashboard'))
            
    return render_template("account/login.html", logged_in=current_user.is_authenticated)

@account.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('website.home'))

# ***********************************************************************************************
# DASHBOARDs
# displaying user dashboard after log-in according to the account type: user, author, or admin
@account.route("/dashboard")
@login_required
def dashboard():
    if current_user.type == "user":
        latest_posts = db.session.query(Blog_Posts).filter(
            Blog_Posts.admin_approved == "TRUE", Blog_Posts.date_to_post <= datetime.utcnow()).order_by(desc(Blog_Posts.date_to_post)).limit(3)
        latest_bookmarks = Blog_Bookmarks.query.filter_by(user_id=current_user.id).limit(9)
        if latest_bookmarks.count() == 0:
            latest_bookmarks = None
        return render_template('account/dashboard_user.html', name=current_user.name, logged_in=True, latest_posts=latest_posts, latest_bookmarks=latest_bookmarks)
    elif current_user.type == "author":
        posts_pending_admin = Blog_Posts.query.filter(Blog_Posts.admin_approved == "FALSE").filter(
            Blog_Posts.author_id == current_user.id).all()
        return render_template('account/dashboard_author_dash.html', name=current_user.name, logged_in=True, posts_pending_admin=posts_pending_admin)
    else:
        current_stats = Blog_Stats.query.get_or_404(1)
        posts_pending_approval = Blog_Posts.query.filter_by(
            admin_approved="FALSE").all()
        return render_template('account/dashboard_admin_dash.html', name=current_user.name, logged_in=True, posts_pending_approval=posts_pending_approval, current_stats=current_stats)

# ***********************************************************************************************
# OWN ACCOUNT MANAGEMENT, BOOKMARKS, HISTORY

# Managing own account information - available to all users
@account.route("/dashboard/manage_account")
@login_required
def manage_acct():
    return render_template("account/account_mgmt.html", logged_in=current_user.is_authenticated)

# Update own account information
@account.route("/dashboard/manage_account/update/<int:id>", methods=["GET", "POST"])
@login_required
def update_own_acct_info(id):
    form = The_Accounts()
    from app.repositories.user_repository import UserRepository
    user_at_hand = UserRepository.get_by_id(id)

    if form.validate_on_submit():
        status = UserService.update_user_info(id, form)
        if status == "success":
            flash("Account information updated successfully!")
            return redirect(url_for('account.manage_acct'))
        else:
            flash("Oops, error updating account information (username or email might be taken).")
            return redirect(url_for('account.manage_acct'))

    form.username.data = user_at_hand.name
    form.email.data = user_at_hand.email
    form.about.data = user_at_hand.about
    return render_template("account/account_mgmt_update.html", logged_in=current_user.is_authenticated, form=form)

# Update account information: changing the picture
@account.route("/dashboard/manage_account/update_picture/<int:id>", methods=["GET", "POST"])
@login_required
def update_own_acct_picture(id):
    form = The_Accounts()
    from app.repositories.user_repository import UserRepository
    user_at_hand = UserRepository.get_by_id(id)
    
    profile_picture = user_at_hand.picture if (user_at_hand.picture and user_at_hand.picture != "") else None

    if request.method == "POST" and form.picture.data:
        status = UserService.update_profile_picture(id, request.files['picture'])
        
        if status == "success":
            flash("Picture updated successfully!")
            return redirect(url_for('account.manage_acct'))
        elif status == "invalid_extension":
            flash("Sorry, this image extension is not allowed.")
        else:
            flash("Oops, error updating profile picture, try again.")
            
    return render_template("account/account_mgmt_picture.html", logged_in=current_user.is_authenticated, form=form, profile_picture=profile_picture)


# Delete account
# When an account is deleted, this changes the number of active users in the stats
# When this user is deleted, their picture, bookmarks, and likes are deleted as well.
# If this user is an author, the authorship of the post will be transfered to the blog team.
@account.route("/dashboard/manage_account/delete/<int:id>", methods=["GET", "POST"])
@login_required
def delete_own_acct(id):
    if request.method == "POST":
        status = UserService.delete_account(id)
        
        if status == "success":
            flash("Your account was deleted successfully.")
            return redirect(url_for("website.home"))
        elif status == "cannot_delete_admin":
            flash("Authorization denied: this user cannot be deleted")
            return redirect(url_for('account.manage_acct'))
        else:
            flash("There was a problem deleting your account.")
            return redirect(url_for('account.manage_acct'))
            
    return render_template("account/account_mgmt_delete.html", logged_in=current_user.is_authenticated)

# INBOX
# User can see their comments and replies the comment received.
@account.route("/dashboard/inbox", methods=["GET", "POST"])
@login_required
def inbox():
    users_comments = db.session.query(Blog_Comments).filter(
        Blog_Comments.user_id == current_user.id).order_by(desc(Blog_Comments.date_submitted)).limit(25)

    replies = Blog_Replies.query.filter(
        Blog_Replies.comment_id.in_([c.id for c in users_comments])).all()
    
    if users_comments.count() == 0:
        users_comments = None

    return render_template("account/inbox.html", logged_in=current_user.is_authenticated, users_comments=users_comments, replies=replies)

