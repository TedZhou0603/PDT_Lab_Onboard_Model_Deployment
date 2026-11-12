import torch
from PIL import Image, ImageOps
from torchvision.transforms.functional import to_tensor
from alpamayo1_5.models.alpamayo1_5 import Alpamayo1_5
from alpamayo1_5 import helper
import time 
import cv2
import numpy as np
import socket

number_of_images = 2
#images = Image.open("./workspace/images/camera0.png").convert("RGB")
start = time.perf_counter()
image1 = Image.open("/workspace/images/camera0.png").convert("RGB")
image2 = Image.open("/workspace/images/camera1.png").convert("RGB")
image1 = ImageOps.fit(image1, (1920, 1080), method=Image.Resampling.LANCZOS) # Turn from 2064x1544 to 1920x1080
image2 = ImageOps.fit(image2, (1920, 1080), method=Image.Resampling.LANCZOS)

#frames = to_tensor(image).unsqueeze(0)
frames = torch.stack([
    torch.from_numpy(np.array(image1)).permute(2, 0, 1),
    torch.from_numpy(np.array(image2)).permute(2, 0, 1)
])
print("Frame shape: ", frames.shape)
print("image 1 size: ", image1.size)
print("image 2 size: ", image2.size)
print("Original frames:")
print("Min:", frames.min().item())
print("Max:", frames.max().item())
print("Mean:", frames.float().mean().item())
for i, frame in enumerate(frames):
    img = frame.permute(1, 2, 0).cpu().numpy()
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(f"/workspace/Alpamayo1.5/frame_{i}.png", img)

model = Alpamayo1_5.from_pretrained("nvidia/Alpamayo-1.5-10B", dtype=torch.bfloat16).to("cuda")
processor = helper.get_processor(model.tokenizer)
print(f"Startup time: {time.perf_counter() - start:.3f} seconds")
ros_socket = socket.create_connection(("127.0.0.1", 5000))
while True:
    question = input("\n Ask the model a question or write x to exit")

    if question.lower() == 'x':
        break

    messages = helper.create_vqa_message(frames,question=question,num_frames_per_camera=number_of_images,)

    inputs = processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=False,continue_final_message=True,return_dict=True,return_tensors="pt",)
    
    pixels = inputs["pixel_values"]

    print("Processed pixels:")
    print("Min:", pixels.min().item())
    print("Max:", pixels.max().item())
    print("Mean:", pixels.float().mean().item())
    print("\nProcessor output:")
    for key, value in inputs.items():
        if isinstance(value, torch.Tensor):
            print(
                key,
                "shape:", value.shape,
                "min:", value.min().item(),
                "max:", value.max().item()
            )
        else:
            print(key, type(value))
    model_inputs = helper.to_device({"tokenized_data": inputs}, "cuda")
    torch.cuda.synchronize()
    # Generate answer
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()

    inference_start = time.perf_counter()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        result = model.generate_text(data=model_inputs,top_p=0.98,temperature=0.6,num_samples=1,max_generation_length=256)
    torch.cuda.synchronize()
    inference_time = time.perf_counter() - inference_start

    print("\n--- Performance Metrics ---")
    print(f"Inference latency: {inference_time:.3f} seconds")
    print(f"Inference frequency: {1 / inference_time:.3f} Hz")
    print(f"Images processed: {number_of_images}")
    print(f"Image throughput: {number_of_images / inference_time:.3f} images/sec")
    print(f"Peak GPU allocated memory: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GiB")
    print(f"Peak GPU reserved memory: {torch.cuda.max_memory_reserved() / 1024**3:.2f} GiB")
    print("\nQuestion:", question)
    print("Alpamayo Answer:", result["answer"][0])
    answer = str(result["answer"][0])
    ros_socket.sendall((answer.replace("\n", " ") + "\n").encode("utf-8"))
    #ros_socket.sendall(("Inference latency: " + str(inference_time) + "\n").encode("utf-8"))
    #ros_socket.sendall(("Inference frequency: " + str(1 / inference_time) + "\n").encode("utf-8"))
    #ros_socket.sendall(("Images Processed: " + str(number_of_images) + "\n").encode("utf-8"))
    #ros_socket.sendall(("Image Throughput: " + str(number_of_images / inference_time:) + "\n").encode("utf-8"))
    #ros_socket.sendall(("Images Processed: " + str(inference_time) + "\n").encode("utf-8"))

ros_socket.close()