import os
from time import time
from keras.preprocessing.image import ImageDataGenerator
from keras.backend import clear_session
from keras.optimizers import SGD
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import joblib
from keras.preprocessing import image
from keras.applications import InceptionV3
from keras.models import Sequential, Model, load_model
from keras.layers import Dense, Dropout, Flatten, AveragePooling2D
from keras.callbacks import ModelCheckpoint, TensorBoard, LearningRateScheduler
from keras import initializers, regularizers

# No kruft plz
clear_session()

# Config
height = 299
width = height
num_channels = 3
num_classes = 5
GENERATOR_BATCH_SIZE = 32
TOTAL_EPOCHS = 100
STEPS_PER_EPOCH = 500
VALIDATION_STEPS = 100
weights_file = "weights.best_inception" + str(height) + ".hdf5"

conv_base = InceptionV3(
    weights='imagenet', 
    include_top=False, 
    input_shape=(height, width, num_channels)
)

# First time run, no unlocking
# conv_base.trainable = False
# Let's unlock trainable layers in conv_base by name
set_trainable = False
for layer in conv_base.layers:
    if layer.name == 'conv2d_56':
        set_trainable = True
    if set_trainable:
        layer.trainable = True
    else:
        layer.trainable = False
# Let's unlock by layer level
# for layer in conv_base.layers[:172]:
#    layer.trainable = False
# for layer in conv_base.layers[172:]:
#    layer.trainable = True


# Let's see it
print('Summary')
print(conv_base.summary())

# Let's construct that top layer replacement
x = conv_base.output
x = AveragePooling2D(pool_size=(8, 8))(x)
x - Dropout(0.4)(x)
x = Flatten()(x)
x = Dense(256, activation='relu', kernel_initializer=initializers.he_normal(seed=None), kernel_regularizer=regularizers.l2(.0005))(x)
x = Dropout(0.5)(x)
# Essential to have another layer for better accuracy
x = Dense(128,activation='relu', kernel_initializer=initializers.he_normal(seed=None))(x)
x = Dropout(0.25)(x)
predictions = Dense(num_classes,  kernel_initializer="glorot_uniform", activation='softmax')(x)

print('Stacking New Layers')
model=Model(inputs = conv_base.input, outputs=predictions)

# Load checkpoint if one is found
if os.path.exists(weights_file):
        print ("loading ", weights_file)
        model.load_weights(weights_file)

# checkpoint
filepath = weights_file
checkpoint = ModelCheckpoint(
    filepath, monitor='val_acc', verbose=1, save_best_only=True, mode='max')

# Update info
tensorboard = TensorBoard(log_dir="logs/{}".format(time()))

# Slow down training deeper into dataset
def schedule(epoch):
    if epoch < 6:
        # Warmup model first
        return .0000032
    elif epoch < 12:
        return .01
    elif epoch < 20:
        return .002
    elif epoch < 40:
        return .0004
    elif epoch < 60:
        return .00008
    elif epoch < 80:
        return .000016
    else:
        return .0000032       
lr_scheduler = LearningRateScheduler(schedule)


callbacks_list = [lr_scheduler, checkpoint, tensorboard]

print('Compile model')
# originally adam, but research says SGD with scheduler
# opt = Adam(lr=0.001, amsgrad=True)
opt = SGD(lr=.01, momentum=.9)
model.compile(
    loss='categorical_crossentropy',
    optimizer=opt,
    metrics=['accuracy']
)

train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=30,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.2,
    zoom_range=0.2,
    channel_shift_range=20,
    horizontal_flip=True,
    fill_mode='nearest'
)

# Validation data should not be modified
validation_datagen = ImageDataGenerator(
    rescale=1./255
)

base_dir = 'D:\\nswf_model_training_data\\data'

train_dir = os.path.join(base_dir, 'train')
test_dir = os.path.join(base_dir, 'test')

train_generator = train_datagen.flow_from_directory(
    train_dir,
    target_size=(height, width),
    class_mode='categorical',
    batch_size=GENERATOR_BATCH_SIZE
)

validation_generator = validation_datagen.flow_from_directory(
    test_dir,
    target_size=(height, width),
    class_mode='categorical',
    batch_size=GENERATOR_BATCH_SIZE
)

# Comment in this line if you're looking to reload the last model for training
# Essentially, not taking the best validation weights but to add more epochs
# print ('Starting from last full model run')
# model = load_model("nsfw." + str(width) + "x" + str(height) + ".h5")

print('Start training!')
history = model.fit_generator(
    train_generator,
    callbacks=callbacks_list,
    epochs=TOTAL_EPOCHS,
    steps_per_epoch=STEPS_PER_EPOCH,
    shuffle=True,
    # having crazy threading issues
    # set workers to zero if you see an error like: 
    # `freeze_support()`
    workers=0,
    use_multiprocessing=True,
    validation_data=validation_generator,
    validation_steps=VALIDATION_STEPS
)

# Save it for later
print('Saving Model')
model.save("nsfw." + str(width) + "x" + str(height) + ".h5")
