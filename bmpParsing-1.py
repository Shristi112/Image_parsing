import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np
import struct

byte_order = "little"
file_size = 0
first_px_addr = 0
post_px_addr = 0
img_width = 0
img_height = 0
bytes_per_px = 0
pixels = None

def uint(chunk):
    return int.from_bytes(chunk, byteorder=byte_order, signed=False)


def uint8(chunk, index):
    return index+1, uint(chunk[index:index+1])


def uint16(chunk, index):
    return index+2, uint(chunk[index:index+2])


def uint32(chunk, index):
    return index+4, uint(chunk[index:index+4])


def uint64(chunk, index):
    return index+8, uint(chunk[index:index+8])


def get_string(chunk, index, length):
    return index+length, chunk[index:index+length].decode('utf-8')


class BitParser:
    def __init__(self, master):
        self.master = master
        self.master.title("BMP Editor")

        self.bmp_image = None
        self.modified_image = None

        # Create UI elements
        self.open_button = tk.Button(self.master, text="Open BMP", command=self.open_bmp)
        self.open_button.pack(pady=10)

        self.apply_box_blur_button = tk.Button(self.master, text="Apply Box Blur", command=self.apply_box_blur)
        self.apply_box_blur_button.pack()

        self.apply_gaussian_blur_button = tk.Button(self.master, text="Apply Gaussian Blur",
                                                    command=self.apply_gaussian_blur)
        self.apply_gaussian_blur_button.pack()

        self.apply_prewitt_edge_button = tk.Button(self.master, text="Apply Prewitt Edge Detector",
                                                   command=self.apply_prewitt_edge)
        self.apply_prewitt_edge_button.pack()

        self.save_button = tk.Button(self.master, text="Save BMP", command=self.save_bmp)
        self.save_button.pack(pady=10)

    def open_bmp(self):
        file_path = filedialog.askopenfilename(filetypes=[("BMP files", "*.bmp")])
        if file_path:
            with open(file_path, 'rb') as bmp_file:
                global file_size
                global first_px_addr
                global post_px_addr
                global img_width
                global img_height
                global bytes_per_px
                global pixels

                bmp_header = bmp_file.read(14)
                index = 0

                index, magic = get_string(bmp_header, index, 2)
                print(magic)

                index, file_size = uint32(bmp_header, index)
                print(file_size)

                index, reserved = uint32(bmp_header, index)

                index, first_px_addr = uint32(bmp_header, index)
                print(first_px_addr)

                dib_header_size_bytes = bmp_file.read(4)
                index, dib_header_size = uint32(dib_header_size_bytes, 0)

                dib_header = bmp_file.read(dib_header_size-4)
                index = 0

                index, img_width = uint32(dib_header, index)
                print(img_width)

                index, img_height = uint32(dib_header, index)
                print(img_height)

                index, color_planes = uint16(dib_header, index)

                index, bytes_per_px = uint16(dib_header, index)
                bytes_per_px = bytes_per_px // 8
                print(bytes_per_px)

                # Generate empty numpy array with size [img_height][img_width * 3]
                pixels = np.empty((img_height, img_width, 3), dtype=np.uint8)

                for y in range(img_height):
                    for x in range(img_width):
                        pixel_bytes = bmp_file.read(bytes_per_px)
                        index = 0
                        index, red = uint8(pixel_bytes, index)
                        index, green = uint8(pixel_bytes, index)
                        index, blue = uint8(pixel_bytes, index)
                        pixels[img_height-y-1][x][2] = red
                        pixels[img_height-y-1][x][1] = green
                        pixels[img_height-y-1][x][0] = blue
                post_px_addr = bmp_file.tell()

                self.bmp_image = Image.fromarray(pixels)
                self.display_image(self.bmp_image)

    def apply_filter(self, kernel):
        if self.bmp_image:
            bmp_array = np.array(self.bmp_image)
            modified_array = self.apply_image_effect(bmp_array, kernel)
            self.modified_image = Image.fromarray(modified_array)
            self.display_image(self.modified_image)

    def apply_box_blur(self):
        box_blur_kernel = np.ones((3, 3), dtype=np.float32) / 9.0
        self.apply_filter(box_blur_kernel)

    def apply_gaussian_blur(self):
        gaussian_blur_kernel = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=np.float32) / 16.0
        self.apply_filter(gaussian_blur_kernel)

    def apply_prewitt_edge(self):
        prewitt_kernel = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=np.float32) / 3.0
        self.apply_filter(prewitt_kernel)

    def apply_image_effect(self, image_array, kernel):
        return np.clip(np.convolve(image_array.flatten(), kernel.flatten(), mode='same').reshape(image_array.shape), 0,
                       255).astype(np.uint8)

    def display_image(self, image):
        photo = ImageTk.PhotoImage(image)
        label = tk.Label(self.master, image=photo)
        label.image = photo
        label.pack()

    def save_bmp(self):
        if self.modified_image:
            save_path = filedialog.asksaveasfilename(defaultextension=".bmp", filetypes=[("BMP files", "*.bmp")])
            if save_path:
                # Convert modified image to numpy array
                modified_array = np.array(self.modified_image)

                # Flip the image vertically
                modified_array_flipped = np.flipud(modified_array)

                # Open the new BMP file for writing
                with open(save_path, 'wb') as bmp_file:
                    # Write BMP header
                    bmp_file.write(struct.pack('<2sIHHI', b'BM', 14 + 40 + 3 * img_width * img_height, 0, 0, 14 + 40))

                    # Write DIB header
                    bmp_file.write(
                        struct.pack('<IIIHHIIIIII', 40, img_width, img_height, 1, 24, 0, 3 * img_width * img_height, 0,
                                    0, 0, 0))

                    # Write image data
                    for y in range(img_height):
                        for x in range(img_width):
                            bmp_file.write(
                                struct.pack('BBB', modified_array_flipped[y, x, 2], modified_array_flipped[y, x, 1],
                                            modified_array_flipped[y, x, 0]))

                print("BMP file successfully saved.")


def main():
    root = tk.Tk()
    app = BitParser(root)
    root.mainloop()


if __name__ == "__main__":
    main()
