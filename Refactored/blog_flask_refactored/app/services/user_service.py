import os
from flask import current_app
from app.extensions import db
from app.models.user import Blog_User
from app.models.comments import Blog_Comments, Blog_Replies
from app.models.likes import Blog_Likes
from app.models.bookmarks import Blog_Bookmarks
from app.models.helpers import (
    change_authorship_of_all_post, 
    delete_comment, 
    delete_reply, 
    update_likes, 
    update_bookmarks, 
    update_stats_users_active
)

class UserService:
    @staticmethod
    def delete_user_cascade(user_id):
        """
        Executa a exclusão completa de um usuário, limpando ou reatribuindo
        todos os dados relacionados (Posts, Comentários, Likes, Arquivos).
        """
        user_to_delete = Blog_User.query.get_or_404(user_id)
        
        if user_id == 1:
            return False, "Authorization error: this user cannot be deleted"

        try:
            if user_to_delete.type == "author":
                change_authorship_of_all_post(user_to_delete.id, 2)

            if user_to_delete.comments:
                comments = Blog_Comments.query.filter_by(user_id=user_to_delete.id).all()
                for comment in comments:
                    comment.user_id = 3
                    delete_comment(comment.id)

            if user_to_delete.replies:
                replies = Blog_Replies.query.filter_by(user_id=user_to_delete.id).all()
                for reply in replies:
                    reply.user_id = 3
                    delete_reply(reply.id)

            if user_to_delete.likes:
                likes = Blog_Likes.query.filter_by(user_id=user_to_delete.id).all()
                for like in likes:
                    db.session.delete(like)
                    update_likes(-1)
            
            if user_to_delete.bookmarks:
                bookmarks = Blog_Bookmarks.query.filter_by(user_id=user_to_delete.id).all()
                for bookmark in bookmarks:
                    db.session.delete(bookmark)
                    update_bookmarks(-1)

            UserService._delete_profile_picture(user_to_delete.picture)

            db.session.delete(user_to_delete)
            db.session.commit()
            
            update_stats_users_active(-1)
            
            return True, "User deleted successfully."

        except Exception as e:
            db.session.rollback()
            return False, "There was a problem deleting this user."

    @staticmethod
    def _delete_profile_picture(picture_filename):
        if not picture_filename or picture_filename == "Picture_default.jpg":
            return

        folder = current_app.config["PROFILE_IMG_FOLDER"]
        path = os.path.join(folder, picture_filename)
        
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass