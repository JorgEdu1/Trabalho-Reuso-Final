import os
from flask import current_app
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.posts import Blog_Posts
from app.dashboard.helpers import (
    check_blog_picture,
    delete_blog_img,
)


class PostService:
    @staticmethod
    def create_post_entry(form, author_id):
        """Cria o registro do post no banco de dados."""
        try:
            post = Blog_Posts(
                theme_id=form.theme.data,
                date_to_post=form.date.data,
                title=form.title.data,
                intro=form.intro.data,
                body=form.body.data,
                picture_v_source=form.picture_v_source.data,
                picture_h_source=form.picture_h_source.data,
                picture_s_source=form.picture_s_source.data,
                picture_alt=form.picture_alt.data,
                meta_tag=form.meta_tag.data,
                title_tag=form.title_tag.data,
                author_id=author_id,
            )
            db.session.add(post)
            db.session.commit()
            return post
        except Exception:
            db.session.rollback()
            return None

    @staticmethod
    def update_post_entry(post, form):
        """Atualiza os dados de texto de um post existente."""
        try:
            post.theme_id = form.theme.data
            post.date_to_post = form.date.data
            post.title = form.title.data
            post.intro = form.intro.data
            post.body = form.body.data
            post.picture_v_source = form.picture_v_source.data
            post.picture_h_source = form.picture_h_source.data
            post.picture_s_source = form.picture_s_source.data
            post.picture_alt = form.picture_alt.data
            post.meta_tag = form.meta_tag.data
            post.title_tag = form.title_tag.data

            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def handle_post_images(post, form, request_files, is_update=False):
        """
        Processa o upload das 3 imagens.
        Se is_update=True, deleta a imagem antiga antes de salvar a nova.
        """
        img_status = {"missing": False, "error": False, "size_error": False}

        formats = [
            ("v", form.picture_v, form.picture_v_size, post.picture_v),
            ("h", form.picture_h, form.picture_h_size, post.picture_h),
            ("s", form.picture_s, form.picture_s_size, post.picture_s),
        ]

        for suffix, field_data, field_size, current_img_name in formats:
            if field_size.data and int(field_size.data) > 1500000:
                img_status["size_error"] = True
                continue

            if field_data.data and int(field_size.data) < 1500000:
                filename = secure_filename(field_data.data.filename)

                if is_update and current_img_name:
                    delete_blog_img(current_img_name)

                success = PostService._save_single_image(
                    post, filename, suffix, request_files
                )
                if not success:
                    img_status["error"] = True

            elif not is_update and not field_data.data:
                img_status["missing"] = True

        return img_status

    @staticmethod
    def _save_single_image(post, filename, suffix, request_files):
        """Método auxiliar privado para salvar uma única imagem."""
        try:
            new_img_name = check_blog_picture(post.id, filename, suffix)
            if new_img_name:
                file_key = f"picture_{suffix}"
                file_obj = request_files[file_key]
                # Salva no disco
                save_path = os.path.join(
                    current_app.config["BLOG_IMG_FOLDER"], new_img_name
                )
                file_obj.save(save_path)
                # Atualiza referência no objeto post
                if suffix == "v":
                    post.picture_v = new_img_name
                elif suffix == "h":
                    post.picture_h = new_img_name
                elif suffix == "s":
                    post.picture_s = new_img_name

                db.session.commit()
                return True
        except Exception:
            return False
        return False
