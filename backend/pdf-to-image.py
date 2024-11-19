import fitz  # PyMuPDF
from PIL import Image
import os
import shutil


def calculate_dimensions(original_width, original_height, max_size):
    """
    Calculate new dimensions while maintaining aspect ratio.

    Args:
        original_width (int): Original width of the image
        original_height (int): Original height of the image
        max_size (tuple): Maximum allowed dimensions (width, height)

    Returns:
        tuple: New dimensions (width, height)
    """
    max_width, max_height = max_size
    aspect_ratio = original_width / original_height

    if original_width > original_height:
        # Landscape orientation
        new_width = min(original_width, max_width)
        new_height = int(new_width / aspect_ratio)

        if new_height > max_height:
            new_height = max_height
            new_width = int(new_height * aspect_ratio)
    else:
        # Portrait orientation
        new_height = min(original_height, max_height)
        new_width = int(new_height * aspect_ratio)

        if new_width > max_width:
            new_width = max_width
            new_height = int(new_width / aspect_ratio)

    return new_width, new_height


def convert_pdf_to_images(pdf_path, output_folder="pdf_images", max_size=(1024, 1024)):
    """
    Convert all pages of a PDF to images while maintaining aspect ratio.

    Args:
        pdf_path (str): Path to the PDF file
        output_folder (str): Name of the folder where images will be saved
        max_size (tuple): Maximum allowed dimensions (width, height)

    Returns:
        tuple: (success_count, total_pages)
    """
    try:
        # Create output folder (remove if exists)
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)

        # Open the PDF file
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        success_count = 0

        # Convert each page
        for page_number in range(total_pages):
            try:
                # Get the page
                page = pdf_document[page_number]

                # Set a higher zoom factor for better quality
                zoom = 2
                mat = fitz.Matrix(zoom, zoom)

                # Get the page's pixmap (image)
                pix = page.get_pixmap(matrix=mat)

                # Convert pixmap to PIL Image
                img_data = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Calculate new dimensions maintaining aspect ratio
                new_width, new_height = calculate_dimensions(
                    img_data.width, img_data.height, max_size
                )

                # Resize to calculated dimensions
                img_data = img_data.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS
                )

                # Create output filename
                output_file = os.path.join(
                    output_folder,
                    f"page_{page_number + 1:03d}.png",  # Format: page_001.png
                )

                # Save the image
                img_data.save(output_file, "PNG")
                success_count += 1

                print(
                    f"Converted page {page_number + 1}/{total_pages} "
                    f"({new_width}x{new_height})"
                )

            except Exception as e:
                print(f"Error converting page {page_number + 1}: {str(e)}")
                continue

        # Close the PDF
        pdf_document.close()

        return success_count, total_pages

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return 0, 0


def get_pdf_info(pdf_path):
    """
    Get basic information about the PDF file.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        dict: PDF information
    """
    try:
        pdf_document = fitz.open(pdf_path)
        info = {
            "total_pages": len(pdf_document),
            "file_size": os.path.getsize(pdf_path) / (1024 * 1024),  # in MB
            "filename": os.path.basename(pdf_path),
        }
        pdf_document.close()
        return info
    except Exception as e:
        print(f"Error getting PDF info: {str(e)}")
        return None


# Example usage
if __name__ == "__main__":
    pdf_path = "test-glossary.pdf"
    # pdf_path = "test-glossary.pdf"
    output_folder = "pdf_images"
    max_size = (1024, 1024)  # Maximum dimensions for output images

    # Get PDF information
    pdf_info = get_pdf_info(pdf_path)
    if pdf_info:
        print("\nPDF Information:")
        print(f"Filename: {pdf_info['filename']}")
        print(f"Total pages: {pdf_info['total_pages']}")
        print(f"File size: {pdf_info['file_size']:.2f} MB")
        print(f"\nStarting conversion (max size: {max_size[0]}x{max_size[1]})...")

        # Convert PDF to images
        success_count, total_pages = convert_pdf_to_images(
            pdf_path, output_folder, max_size
        )

        print(f"\nConversion completed!")
        print(f"Successfully converted {success_count} out of {total_pages} pages")
        print(f"Images saved in folder: {output_folder}")
    else:
        print("Failed to read PDF information")
