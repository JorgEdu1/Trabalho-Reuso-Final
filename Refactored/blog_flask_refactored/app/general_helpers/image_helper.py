import os
from flask import current_app
from werkzeug.utils import secure_filename

class ImageHelper:
    
    def check_image_filename(self, filename):
        """
        This function checks whether a picture has the right file extension.
        The function will return "True" if the file extension is correct or "False" if it is not.
        Argument: the filename is the only required argument.
        """

        # Check the filename to see if extension is valid, and to check whether two extensions might be present (eg: .jpg.php)
        if not "." in filename:
            return False

        extension = filename.rsplit(".", 1)[1]

        if extension.upper() not in current_app.config["ALLOWED_IMG_EXTENSIONS"]:
            return False

        if filename.count('.') > 1:
            return False

        else:
            return True

    def check_blog_picture(self, post_id, filename, db_column):
        """
        This function checks whether a picture uploaded to a blog post has the right file extension and gives the picture a new name.
        If the file extension is not supported, it returns 'False'
        Arguments: the post's id, the filename, and the database column where it should be added: "v", "h", or "s".
        """
        
        # Check supplied arguments
        if db_column == "v" or db_column == "h" or db_column == "s":
            if type(post_id) is not int:
                return False
            
            # A única mudança real: adicionamos 'self.' para chamar o método vizinho
            if not self.check_image_filename(filename):
                return False
            
            # return new filename:
            post_id_str = str(post_id)
            extension = filename.rsplit(".", 1)[1]
            pic_new_name = "Picture_" + db_column + "_" + post_id_str + "." + extension
            return pic_new_name
        else:
            return False

    def delete_blog_img(self, img):
        """Accepts blog image name and deletes it from folder or raises name error."""
        if img != None and os.path.exists(os.path.join(current_app.config["BLOG_IMG_FOLDER"], img)):
            try:
                os.remove(os.path.join(current_app.config["BLOG_IMG_FOLDER"], img))
            except:
                raise NameError("Blog post image could not be deleted.")

    # --- Funções que vieram do models/helpers.py (Mantendo nomes originais) ---
    
    def pic_src_post(self, picture_name):
        return f"../static/Pictures_Posts/{picture_name}"

    def pic_src_theme(self, picture_name):
        return f"../static/Pictures_Themes/{picture_name}"

    def pic_src_user(self, picture_name):
        return f"../static/Pictures_Users/{picture_name}"