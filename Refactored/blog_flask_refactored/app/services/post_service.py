import os
from flask import current_app, flash
from werkzeug.utils import secure_filename
from app.repositories.post_repository import PostRepository
from app.models.posts import Blog_Posts

#from app.dashboard.helpers import check_blog_picture, delete_blog_img
from app.general_helpers.image_helper import ImageHelper
from app.models.helpers import update_approved_post_stats


class PostService:
    @staticmethod
    def _handle_and_save_image(post_id, file_storage, img_type):
        helper = ImageHelper()
        if not file_storage:
            return None

        filename = secure_filename(file_storage.filename)
        new_img_name = helper.check_blog_picture(post_id, filename, img_type)
        
        if new_img_name:
            save_path = os.path.join(current_app.config["BLOG_IMG_FOLDER"], new_img_name)
            file_storage.save(save_path)
            
            return new_img_name
        
        return None

    @staticmethod
    def create_post(form, author_id):

        post = Blog_Posts(
            theme_id=form.theme.data,
            date_to_post=form.date.data,
            title=form.title.data,
            intro=form.intro.data,
            body=form.body.data,
            picture_alt=form.picture_alt.data,
            meta_tag=form.meta_tag.data,
            title_tag=form.title_tag.data,
            author_id=author_id,
            picture_v_source=form.picture_v_source.data,
            picture_h_source=form.picture_h_source.data,
            picture_s_source=form.picture_s_source.data
        )
        
        post = PostRepository.add(post)

        try:
            has_changes = False

            if form.picture_v.data:
                saved_name = PostService._handle_and_save_image(post.id, form.picture_v.data, "v")
                if saved_name:
                    post.picture_v = saved_name
                    has_changes = True

            if form.picture_h.data:
                saved_name = PostService._handle_and_save_image(post.id, form.picture_h.data, "h")
                if saved_name:
                    post.picture_h = saved_name
                    has_changes = True

            if form.picture_s.data:
                saved_name = PostService._handle_and_save_image(post.id, form.picture_s.data, "s")
                if saved_name:
                    post.picture_s = saved_name
                    has_changes = True
            
            if has_changes:
                PostRepository.update()
            
        except Exception as e:
            flash(f"Post criado, mas erro ao salvar imagens: {str(e)}", "warning")
            print(f"DEBUG ERROR IMAGE: {e}")
            
        return post

    @staticmethod
    def update_post(post_id, form):
        helper = ImageHelper()
        post = PostRepository.get_by_id(post_id)
        
        post.theme_id = form.theme.data
        post.date_to_post = form.date.data
        post.title = form.title.data
        post.intro = form.intro.data
        post.body = form.body.data
        post.picture_alt = form.picture_alt.data
        post.meta_tag = form.meta_tag.data
        post.title_tag = form.title_tag.data
        post.picture_v_source = form.picture_v_source.data
        post.picture_h_source = form.picture_h_source.data
        post.picture_s_source = form.picture_s_source.data

        try:
            if form.picture_v.data:
                if post.picture_v: helper.delete_blog_img(post.picture_v) # Apaga velha
                post.picture_v = PostService._handle_and_save_image(post.id, form.picture_v.data, "v")

            if form.picture_h.data:
                if post.picture_h: helper.delete_blog_img(post.picture_h)
                post.picture_h = PostService._handle_and_save_image(post.id, form.picture_h.data, "h")

            if form.picture_s.data:
                if post.picture_s: helper.delete_blog_img(post.picture_s)
                post.picture_s = PostService._handle_and_save_image(post.id, form.picture_s.data, "s")

            PostRepository.update()
        except Exception as e:
             flash(f"Erro ao atualizar imagens: {str(e)}", "warning")

        return post

    @staticmethod
    def delete_post(post_id):
        helper = ImageHelper()
        post = PostRepository.get_by_id(post_id)
        
        if post.admin_approved == "TRUE":
            update_approved_post_stats(-1)
            
        imgs_to_delete = [post.picture_v, post.picture_h, post.picture_s]
        
        PostRepository.delete_with_cascade(post)
        
        for img in imgs_to_delete:
            if img: helper.delete_blog_img(img)

    @staticmethod
    def get_themes():
        return PostRepository.get_themes()
    
    @staticmethod
    def get_post_by_id(post_id):
        return PostRepository.get_by_id(post_id)
    
    @staticmethod
    def approve_post(post_id):
        post = PostRepository.get_by_id(post_id)
        
        post.admin_approved = "TRUE"
        
        PostRepository.update()
        
        update_approved_post_stats(1)
        
        return "success"

    @staticmethod
    def disallow_post(post_id):
        post = PostRepository.get_by_id(post_id)
        
        post.admin_approved = "FALSE"
        
        PostRepository.update()
        
        update_approved_post_stats(-1)
        
        return "success"