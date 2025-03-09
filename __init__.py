import os
import folder_paths
from PIL import Image, ImageDraw, ImageFont
import torch
import numpy as np
from datetime import datetime

class FolderImagesPreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "images_per_row": ("INT", {"default": 5, "min": 1, "max": 20, "step": 1}),
                "include_subfolders": ("BOOLEAN", {"default": False}),
                "background_color": ("STRING", {"default": "#FFFFFF", "multiline": False}),  
                "text_color": ("STRING", {"default": "#000000", "multiline": False}),   
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "generate_preview"
    CATEGORY = "💀Folder Images Preview"

    def generate_preview(self, folder_path, images_per_row, include_subfolders, background_color, text_color):
        # Supported image formats
        supported_formats = (".png", ".jpg", ".jpeg", ".gif", ".tiff", ".webp", ".bmp")
        
        # Check if folder exists
        if not os.path.isdir(folder_path):
            raise ValueError(f"The folder path '{folder_path}' does not exist or is not a directory!")

        # Get font path
        font_path = os.path.join(os.path.dirname(__file__), "font", "lanting.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Font file '{font_path}' not found!")

        # Convert HEX colors to RGB tuples
        try:
            bg_color = tuple(int(background_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            txt_color = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            raise ValueError("Background color or text color must be a valid HEX value, e.g., #FFFFFF")

        # Get image files
        image_files = []
        if include_subfolders:
            for root, _, files in os.walk(folder_path):
                subfolder_images = [(root, f) for f in files if f.lower().endswith(supported_formats)]
                if subfolder_images:
                    image_files.append(subfolder_images)
        else:
            image_files = [[(folder_path, f) for f in os.listdir(folder_path) 
                           if os.path.isfile(os.path.join(folder_path, f)) 
                           and f.lower().endswith(supported_formats)]]
        
        total_images = sum(len(subfolder) for subfolder in image_files)

        # Parameter settings
        thumbnail_size = 256  # Image area size
        text_height = 60      # Filename area height (supports two lines)
        grid_spacing = 48     # Grid spacing
        stats_height = 40     # Statistics text height
        footer_height = 40    # Footer text height
        subfolder_title_height = 40  # Subfolder title height
        line_thickness = 2    # Divider line thickness
        
        # Calculate canvas height
        output_width = images_per_row * thumbnail_size + (images_per_row + 1) * grid_spacing
        if total_images == 0:
            output_height = (grid_spacing + stats_height + grid_spacing +  # Top stats
                            line_thickness +  # Top divider
                            grid_spacing +  # Space below top divider
                            grid_spacing +  # Space above bottom divider
                            line_thickness +  # Bottom divider
                            footer_height + grid_spacing)  # Footer and bottom padding
        else:
            if include_subfolders:
                rows = sum((len(subfolder) + images_per_row - 1) // images_per_row for subfolder in image_files)
                output_height = (grid_spacing + stats_height + grid_spacing +  # Top with divider
                                line_thickness + grid_spacing +  # Top divider and spacing
                                len(image_files) * (subfolder_title_height + grid_spacing) +  # Subfolder titles
                                rows * (thumbnail_size + text_height + grid_spacing) +  # Image rows
                                grid_spacing + line_thickness +  # Bottom divider with spacing
                                footer_height + grid_spacing)  # Footer and bottom padding
            else:
                rows = (total_images + images_per_row - 1) // images_per_row
                output_height = (grid_spacing + stats_height + grid_spacing +  # Top with divider
                                line_thickness + grid_spacing +  # Top divider and spacing
                                rows * (thumbnail_size + text_height + grid_spacing) +  # Image rows
                                grid_spacing + line_thickness +  # Bottom divider with spacing
                                footer_height + grid_spacing)  # Footer and bottom padding

        # Create blank canvas
        output_image = Image.new("RGB", (output_width, output_height), bg_color)
        draw = ImageDraw.Draw(output_image)

        # Load font
        try:
            font = ImageFont.truetype(font_path, 20)
            stats_font = ImageFont.truetype(font_path, 24)
        except Exception as e:
            raise ValueError(f"Failed to load font '{font_path}': {e}")

        # Add top statistics text
        if total_images == 0:
            stats_text = "Not found any image"
        elif total_images == 1:
            stats_text = "Found 1 image"
        else:
            stats_text = f"Found {total_images} images"
        draw.text((grid_spacing, grid_spacing), stats_text, fill=txt_color, font=stats_font)

        # Add top divider line
        line_y_top = grid_spacing + stats_height + grid_spacing
        draw.rectangle([(grid_spacing, line_y_top), (output_width - grid_spacing, line_y_top + line_thickness)], 
                      fill=txt_color)

        # If no images, add bottom divider and time, then return
        current_time = datetime.now().strftime("Created on %Y-%m-%d %H:%M:%S")
        if total_images == 0:
            line_y_bottom = output_height - footer_height - grid_spacing - line_thickness - grid_spacing
            draw.rectangle([(grid_spacing, line_y_bottom), (output_width - grid_spacing, line_y_bottom + line_thickness)], 
                          fill=txt_color)
            draw.text((grid_spacing, line_y_bottom + line_thickness + grid_spacing), 
                     current_time, fill=txt_color, font=stats_font)
            image_array = np.array(output_image).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_array)[None,]
            return (image_tensor,)

        # Process images
        current_y = line_y_top + line_thickness + grid_spacing
        image_idx = 0

        for subfolder_images in image_files:
            if include_subfolders and subfolder_images:  # Show title only if subfolders are enabled
                # Add subfolder title
                subfolder_path = subfolder_images[0][0]
                subfolder_name = os.path.basename(folder_path) if subfolder_path == folder_path else os.path.relpath(subfolder_path, folder_path)
                subfolder_text = f"- {subfolder_name} ({len(subfolder_images)} images)"
                draw.text((grid_spacing, current_y), subfolder_text, fill=txt_color, font=stats_font)
                current_y += subfolder_title_height + grid_spacing

            for root, image_file in subfolder_images:
                image_path = os.path.join(root, image_file)
                try:
                    # Open image
                    img = Image.open(image_path).convert("RGB")
                    
                    # Scale proportionally to 256px, crop if exceeds, fill with text color if smaller
                    img_width, img_height = img.size
                    if img_width > img_height:
                        new_width = thumbnail_size
                        new_height = int(img_height * (thumbnail_size / img_width))
                    else:
                        new_height = thumbnail_size
                        new_width = int(img_width * (thumbnail_size / img_height))
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Create 256x256 blank canvas with text color as background
                    thumbnail = Image.new("RGB", (thumbnail_size, thumbnail_size), txt_color)
                    paste_x = (thumbnail_size - new_width) // 2
                    paste_y = (thumbnail_size - new_height) // 2
                    # Crop if exceeds 256x256
                    if new_width > thumbnail_size or new_height > thumbnail_size:
                        left = (new_width - thumbnail_size) // 2
                        top = (new_height - thumbnail_size) // 2
                        img = img.crop((left, top, left + thumbnail_size, top + thumbnail_size))
                        thumbnail.paste(img, (0, 0))
                    else:
                        thumbnail.paste(img, (paste_x, paste_y))

                    # Calculate grid position
                    row = (image_idx % (len(subfolder_images))) // images_per_row
                    col = (image_idx % (len(subfolder_images))) % images_per_row
                    x = grid_spacing + col * (thumbnail_size + grid_spacing)
                    y = current_y + row * (thumbnail_size + text_height + grid_spacing)

                    # Paste image
                    output_image.paste(thumbnail, (x, y))

                    # Process filename (show path only in subfolder mode)
                    if include_subfolders:
                        rel_path = os.path.relpath(root, folder_path) if root != folder_path else ""
                        filename = os.path.splitext(image_file)[0]
                        display_name = os.path.join(rel_path, filename) if rel_path else filename
                    else:
                        display_name = os.path.splitext(image_file)[0]
                    max_width = thumbnail_size - 10
                    text_y = y + thumbnail_size + 5
                    
                    wrapped_text = self.wrap_text(display_name, font, max_width)
                    if len(wrapped_text) > 2:
                        wrapped_text = wrapped_text[:2]
                        wrapped_text[-1] = wrapped_text[-1].rstrip("...") + "..."

                    for i, line in enumerate(wrapped_text[:2]):
                        draw.text((x + 5, text_y + i * 25), line, fill=txt_color, font=font)

                    image_idx += 1

                except Exception as e:
                    print(f"Error loading image '{image_path}': {e}")
                    continue

            if include_subfolders:
                rows_in_subfolder = (len(subfolder_images) + images_per_row - 1) // images_per_row
                current_y += rows_in_subfolder * (thumbnail_size + text_height + grid_spacing)

        # Add bottom divider and creation time
        line_y_bottom = output_height - footer_height - grid_spacing - line_thickness - grid_spacing
        draw.rectangle([(grid_spacing, line_y_bottom), (output_width - grid_spacing, line_y_bottom + line_thickness)], 
                      fill=txt_color)
        draw.text((grid_spacing, line_y_bottom + line_thickness + grid_spacing), 
                 current_time, fill=txt_color, font=stats_font)

        # Convert PIL image to ComfyUI tensor format
        image_array = np.array(output_image).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_array)[None,]

        return (image_tensor,)

    def wrap_text(self, text, font, max_width):
        """Split text into multiple lines based on width"""
        lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
        
        return lines

# Register node
NODE_CLASS_MAPPINGS = {
    "FolderImagesPreview": FolderImagesPreview
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FolderImagesPreview": "💀Folder Images Preview"
}