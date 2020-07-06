import os
import sys
import numpy as np
import datetime
from mrcnn.config import Config
from mrcnn import model as modellib, utils
import skimage.draw

os.environ["CUDA_VISIBLE_DEVICES"]="0"
# Root directory of the project
ROOT_DIR = os.path.abspath("/home/rinku/deepgis_moon/")
# Import Mask RCNN
sys.path.append(ROOT_DIR)  # To find local version of the library
DEFAULT_LOGS_DIR = os.path.join(ROOT_DIR, "logs")
IMAGE_PATH= "/home/rinku/deepgis_moon/webclient/static/moon-images/tile_3000_22000.png"
COCO_WEIGHTS_PATH = os.path.join(ROOT_DIR, "mask_rcnn_coco.h5")
trained_model_path = os.path.join(ROOT_DIR, "trained_rcnn.h5")
DATASET_DIR = "/home/rinku/deepgis_moon/static-root/labels/npy/"

class CustomConfig(Config):
    """Configuration for training on the toy  dataset.
    Derives from the base Config class and overrides some values.
    """
    # Give the configuration a recognizable name
    NAME = "crater"

    # We use a GPU with 12GB memory, which can fit two images.
    # Adjust down if you use a smaller GPU.
    IMAGES_PER_GPU = 2

    # Number of classes (including background)
    NUM_CLASSES = 1 + 1  # Background + crater

    # Number of training steps per epoch
    STEPS_PER_EPOCH = 10

    # Skip detections with < 90% confidence
    DETECTION_MIN_CONFIDENCE = 0.9

class CustomDataset(utils.Dataset):

    def load_custom(self, dataset_dir, subset):
        """Load a subset of the bottle dataset.
        dataset_dir: Root directory of the dataset.
        subset: Subset to load: train or val
        """
        # Add classes. We have only one class to add.
        self.add_class("crater", 1, "crater")

        # Train or validation dataset?
        assert subset in ["train", "val"]
        if subset == "train":
            pass
        else:
            dataset_dir = os.path.join(dataset_dir, subset)

        # Add images
        for filename in os.listdir(dataset_dir):
            if not filename.endswith(".npy"):
                continue

            # load_mask() needs the image size to convert polygons to masks.
            # Unfortunately, VIA doesn't include it in JSON, so we must read
            # the image. This is only managable since the dataset is tiny.
            a_image = os.path.join(dataset_dir, filename)
            #image = np.load(image_path)

            image_path="/home/rinku/deepgis_moon/webclient/static/moon-images/"+filename[:-4];
            self.add_image(
                "crater",  ## for a single class just add the name here
                image_id=filename,  # use file name as a unique image id
                path=image_path,
                annotation_path=a_image)

    def load_mask(self, image_id):
        """Generate instance masks for an image.
       Returns:
        masks: A bool array of shape [height, width, instance count] with
            one mask per instance.
        class_ids: a 1D array of class IDs of the instance masks.
        """
        # If not a bottle dataset image, delegate to parent class.
        #import time
        #start = time.time()
        image_info = self.image_info[image_id]
        if image_info["source"] != "crater":
            return super(self.__class__, self).load_mask(image_id)

        mask = np.load(image_info["annotation_path"])
        #print("load mask time-",time.time() - start)
        return mask.astype(np.bool), np.ones([mask.shape[-1]], dtype=np.int32)

    def image_reference(self, image_id):
        """Return the path of the image."""
        info = self.image_info[image_id]
        if info["source"] == "crater":
            return info["path"]
        else:
            super(self.__class__, self).image_reference(image_id)

def color_splash(image, mask):
    """Apply color splash effect.
    image: RGB image [height, width, 3]
    mask: instance segmentation mask [height, width, instance count]

    Returns result image.
    """
    # Make a grayscale copy of the image. The grayscale copy still
    # has 3 RGB channels, though.
    gray_true = skimage.color.gray2rgb(skimage.color.rgb2gray(image)) * 101
    gray = skimage.color.gray2rgb(skimage.color.rgb2gray(image)) * 255
    # We're treating all instances as one, so collapse the mask into one layer
    mask = (np.sum(mask, -1, keepdims=True) >= 1)
    # Copy color pixels from the original color image where mask is set
    if mask.shape[0] > 0:
        # result = np.where(mask == True)
        # print(result)
        splash = np.where(mask, gray_true, gray).astype(np.uint8)
    else:
        splash = gray
    return splash

def detect_and_color_splash(model, image_path=None):
    # Image or video?
    if image_path:
        # Run model detection and generate the color splash effect
        print("Running on {}".format(IMAGE_PATH))
        # Read image
        image = skimage.io.imread(IMAGE_PATH)
        # Detect objects
        r = model.detect([image], verbose=1)[0]
        # Color splash
        splash = color_splash(image, r['masks'])
        # Save output
        file_name = IMAGE_PATH[:-3] + "_{:%Y%m%dT%H%M%S}.png".format(datetime.datetime.now())
        skimage.io.imsave(file_name, splash)
    print("Saved to ", file_name)

def train(model):
    """Train the model."""
    # Training dataset.
    dataset_train = CustomDataset()
    dataset_train.load_custom(DATASET_DIR, "train")
    dataset_train.prepare()

    # Validation dataset
    dataset_val = CustomDataset()
    dataset_val.load_custom(DATASET_DIR, "val")
    dataset_val.prepare()

    # *** This training schedule is an example. Update to your needs ***
    # Since we're using a very small dataset, and starting from
    # COCO trained weights, we don't need to train too long. Also,
    # no need to train all layers, just the heads should do it.
    print("Training network heads")
    model.train(dataset_train, dataset_val,
                learning_rate=config.LEARNING_RATE,
                epochs=20,
                layers='heads')
    return model

if __name__ == '__main__':

    config = CustomConfig()
    model = modellib.MaskRCNN(mode="training", config=config,
                              model_dir=DEFAULT_LOGS_DIR)
    weights_path = COCO_WEIGHTS_PATH

    model.load_weights(weights_path, by_name=True, exclude=[
        "mrcnn_class_logits", "mrcnn_bbox_fc",
        "mrcnn_bbox", "mrcnn_mask"])

    trained_model = train(model)
    trained_model.keras_model.save(trained_model_path)

    class InferenceConfig(CustomConfig):
        # Set batch size to 1 since we'll be running inference on
        # one image at a time. Batch size = GPU_COUNT * IMAGES_PER_GPU
        GPU_COUNT = 1
        IMAGES_PER_GPU = 1


    config = InferenceConfig()

    model = modellib.MaskRCNN(mode="inference", config=config,
                              model_dir=DEFAULT_LOGS_DIR)

    model.load_weights(trained_model_path, by_name=True, exclude=[
        "mrcnn_class_logits", "mrcnn_bbox_fc",
        "mrcnn_bbox", "mrcnn_mask"])

    from PIL import Image

    im = Image.open(IMAGE_PATH)
    rgb_im = im.convert('RGB')
    IMAGE_PATH = IMAGE_PATH[:-3] + 'jpg'
    rgb_im.save(IMAGE_PATH)

    detect_and_color_splash(model, image_path=IMAGE_PATH)
#    testset = "/home/rinku/deepgis_moon/webclient/static/moon-images/"
#    for filename in os.listdir(testset):
#      IMAGE_PATH1 = os.path.join(testset, filename)
#      im = Image.open(IMAGE_PATH1)
#      rgb_im = im.convert('RGB')
#      IMAGE_PATH1 = IMAGE_PATH1[:-3] + 'jpg'
#      rgb_im.save(IMAGE_PATH1)
#      detect_and_color_splash(model, image_path=IMAGE_PATH1)
