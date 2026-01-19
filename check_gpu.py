import torch
print(f"Czy CUDA jest dostępna? {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Nazwa karty: {torch.cuda.get_device_name(0)}")
else:
    print("❌ Python nie widzi karty graficznej. Używa CPU.")