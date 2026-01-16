import os
import uuid
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask import current_app

from app.account.helpers import hash_pw
from app.general_helpers.helpers import check_image_filename
from app.models.helpers import update_stats_users_total, update_stats_users_active, update_likes, update_bookmarks, change_authorship_of_all_post
from app.models.user import Blog_User

from app.repositories.user_repository import UserRepository

class UserService:
    @staticmethod
    def signup_user(form):
        if UserRepository.get_by_email(form.email.data):
            return None, "email_exists"
        
        hashed_pw = hash_pw(form.password.data)

        new_user = Blog_User(
            name=form.username.data,
            email=form.email.data,
            password=hashed_pw,
            type="user"
        )

        UserRepository.add(new_user)

        update_stats_users_total()
        update_stats_users_active(1)

        return new_user, "success"

    @staticmethod
    def login_user(email, password):
        user = UserRepository.get_by_email(email)
        
        if not user:
            return None, "email_not_found"
        
        if not check_password_hash(user.password, password):
            return None, "wrong_password"
            
        if user.blocked == "TRUE":
            return None, "blocked"
            
        return user, "success"

    @staticmethod
    def update_user_info(user_id, form):
        user = UserRepository.get_by_id(user_id)
        
        existing_email = UserRepository.get_by_email(form.email.data)
        if existing_email and existing_email.id != user_id:
            return "email_taken"
        
        existing_name = UserRepository.get_by_name(form.username.data)
        if existing_name and existing_name.id != user_id:
            return "username_taken"

        user.name = form.username.data
        user.email = form.email.data
        user.about = form.about.data
        
        UserRepository.update()
        return "success"

    @staticmethod
    def update_profile_picture(user_id, form_picture):
        user = UserRepository.get_by_id(user_id)
        
        pic_filename = secure_filename(form_picture.filename)
        if not check_image_filename(pic_filename):
            return "invalid_extension"

        pic_filename_unique = str(uuid.uuid1()) + "_" + pic_filename
        old_picture = user.picture

        try:
            form_picture.save(os.path.join(
                current_app.config["PROFILE_IMG_FOLDER"], pic_filename_unique))
            
            user.picture = pic_filename_unique
            UserRepository.update()

            if old_picture and old_picture != "Picture_default.jpg":
                old_path = os.path.join(current_app.config["PROFILE_IMG_FOLDER"], old_picture)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            return "success"
        except:
            return "error"

    @staticmethod
    def delete_account(user_id):
        user = UserRepository.get_by_id(user_id)
        
        if user_id == 1:
            return "cannot_delete_admin"

        if user.type == "author":
            change_authorship_of_all_post(user.id, 2)

        if user.picture and user.picture != "Picture_default.jpg":
            pic_path = os.path.join(current_app.config["PROFILE_IMG_FOLDER"], user.picture)
            if os.path.exists(pic_path):
                os.remove(pic_path)

        if user.likes:
            update_likes(-len(user.likes))
        if user.bookmarks:
            update_bookmarks(-len(user.bookmarks))

        UserRepository.delete_account_logic(user)
        
        update_stats_users_active(-1)
        
        return "success"
    
    @staticmethod
    def perform_user_update_logic(user_to_update, form):
        user_to_update.name = form.get("username_update")
        user_to_update.email = form.get("email_update")
        user_to_update.type = form.get("accttype_update")
        
        new_blocked_status = form.get("acctblocked_update")
        user_to_update.blocked = new_blocked_status

        content_status_to_apply = None

        if new_blocked_status == "TRUE":
            content_status_to_apply = "TRUE"
        elif new_blocked_status == "FALSE":
            content_status_to_apply = "FALSE"

        UserRepository.update_user_and_content_status(user_to_update, content_status_to_apply)

    @staticmethod
    def get_by_id(user_id):
        return UserRepository.get_by_id(user_id)
    
    @staticmethod
    def get_by_email(email):
        return UserRepository.get_by_email(email)
    
    @staticmethod
    def get_by_name(name):
        return UserRepository.get_by_name(name)

    @staticmethod
    def block_user(user_id):
        user = UserRepository.get_by_id(user_id)
        if not user:
            return "not_found"

        if user_id == 1:
            return "cannot_block_admin"

        user.blocked = "TRUE"
        
        try:
            UserRepository.update_user_and_content_status(user, content_block_status="TRUE")
            return "success"
        except Exception as e:
            # Logar erro se necessário
            return "error"