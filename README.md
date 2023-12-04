I had a lot of rectangular product images on shopify that where already uploaded and assigned to products that didn't look right on the website (were being cropped to be square) because the recommended product image size is 2048x2048.

There was no shopify feature to bulk resize images. In addition, the images had to be filled and croped because they were rectangular. Luckly the image background was pure black so it was easy to fill the missing part of the image black

This script checks every product image and if the image is rectangular or square but not 2048x2048 it will:
- download the image
- resize it to 2048x2048
- fill background black (0,0,0)
- update product image

for the shopify api you only need the store url and the store access token with product read and write permissions
to get the token go to Apps and Sales channel > Develop Apps > create an App
