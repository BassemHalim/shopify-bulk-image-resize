from PIL import Image
import requests
import os

STORE_URL = "https://<MYSTORE>.myshopify.com"
STORE_ACCESS_TOKEN = ""
graphql_url = STORE_URL + "/admin/api/2023-01/graphql.json"


def make_square(im, min_size=256, fill_color=(0, 0, 0, 0)):
    x, y = im.size
    if x == y:
        return im
    size = max(min_size, x, y)
    new_im = Image.new("RGB", (size, size), fill_color)
    new_im.paste(im, (int((size - x) / 2), int((size - y) / 2)))
    return new_im


def getProducts(cursor):
    query="""
    query Products($cursor: String) {
    products(first: 5, after: $cursor) {
        edges {
            cursor
            node {
                id
                images(first: 10) {
                    nodes {
                        id
                        height
                        width
                        url
                    }
                }
            }
        }
        pageInfo{
            hasNextPage
        }
    }
}
    """
    variables = {"cursor": cursor}
    if cursor:
        data = {"query": query, "variables": variables}
    else:
        data = {"query": query}
        
    response = requests.post(
        url=graphql_url,
        headers={"X-Shopify-Access-Token": STORE_ACCESS_TOKEN},
        json=data,
    )
    if response.ok:
        products = response.json()["data"]["products"]
        hasNext = products['pageInfo']['hasNextPage']
        return products, hasNext


def process_image(url):
    filename = os.path.basename(url)
    filename = filename.split("?")[0]
    # download image
    if not os.path.exists("orig-images/"):
        os.mkdir("orig-images/")
    if not os.path.exists("resized/"):
        os.mkdir("resized")
    download_path = "orig-images/" + filename
    response = requests.get(url, allow_redirects=True)
    with open(download_path, "wb") as file:
        file.write(response.content)
    # resize
    im = Image.open(download_path)
    im = make_square(im)
    resized = im.resize((2048, 2048))
    resized_path = "resized/" + filename
    resized.save(resized_path)
    return filename


def upload_image(filename):
    query = """
mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) 
    {
        stagedTargets {
            url
            resourceUrl
        }
        userErrors {
            field
            message
        }
    }
}
"""
    path = "resized/" + filename
    headers = {
        "X-Shopify-Access-Token": STORE_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    variables = {
        "input": {
            "filename": filename,
            "fileSize": str(os.path.getsize(path)),
            "mimeType": "image/jpeg",
            "resource": "IMAGE",
        }
    }

    data = {"query": query, "variables": variables}
    response = requests.post(graphql_url, headers=headers, json=data)
    if not response.ok:
        print(response.status_code)
        return ""
    result = response.json()
    stagedTargets = result["data"]["stagedUploadsCreate"]["stagedTargets"][0]
    upload_url = stagedTargets["url"]
    resource_url = stagedTargets["resourceUrl"]

    # upload image
    headers = {
        "content_type": "image/jpeg",
        "acl": "private",
    }
    with open(path, "rb") as f:
        data = f.read()
    response = requests.put(upload_url, headers=headers, data=data)
    if not response.ok:
        print(response.status_code)
    return resource_url


def update_product_image(productID, imageID, imageURL):
    query = """
mutation productImageUpdate($productId: ID!, $image: ImageInput!) {
  productImageUpdate(productId: $productId, image: $image) {
    image {
      id
      src
    }
    userErrors {
      field
      message
    }
  }
}

    """
    headers = {
        "X-Shopify-Access-Token": STORE_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    variables = {"productId": productID, "image": {"id": imageID, "src": imageURL}}
    data = {"query": query, "variables": variables}
    response = requests.post(graphql_url, headers=headers, json=data)
    if not response.ok:
        print(response.status_code)
        return ""
    else:
        print("success!!")
        
        
hasNext = True
lastCursor = None
while hasNext:
    products, hasNext = getProducts(lastCursor)
    edges = products['edges']
    for edge in edges:
        product = edge['node']
        lastCursor = edge['cursor']
        images = product["images"]["nodes"]
        productID = product["id"]
        for image in images:
            width, height = image["width"], image["height"]
            imageID = image["id"]
            print(imageID)
            if width != height or width != 2048:
                url = image["url"]
                # download and resize
                resized = process_image(url)
                # upload
                new_url = upload_image(resized)
                # change product image
                update_product_image(productID=productID, imageID=imageID, imageURL=new_url)
