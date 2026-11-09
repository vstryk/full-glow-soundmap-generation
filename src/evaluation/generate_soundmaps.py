import torch
import os
import argparse
from PIL import Image
import pandas as pd
import numpy as np
from torchvision import transforms, utils
from tqdm import tqdm
import helper
import models
from globals import device
from sklearn.preprocessing import MinMaxScaler
import time
import csv
import json
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="Generate soundmaps from test buildings")
    # Bedingungen
    parser.add_argument("--use_temperature", action="store_true", help="Use temperature condition")
    parser.add_argument("--use_humidity", action="store_true", help="Use humidity condition")
    parser.add_argument("--use_db", action="store_true", help="Use dB condition")
    
    # Pfade und Modelltyp
    parser.add_argument("--checkpoint_path", type=str, required=True, 
                       help="Path to model checkpoint directory")
    parser.add_argument("--dataset_path", type=str, required=True,
                       help="Path to test dataset directory")
    parser.add_argument("--output_base", type=str, required=True,
                       help="Base directory for evaluation outputs")
    parser.add_argument("--model_type", type=str, required=True,
                       help="Model training type (with_extra_conditions or without_extra_conditions)")
    
    # Model Parameter
    parser.add_argument("--optim_step", type=int, default=1000000,
                       help="Optimization step to load from checkpoint")
    parser.add_argument("--image_size", type=int, nargs=2, default=[256, 256],
                       help="Image size for generation (height width)")

    # Normierung der Zahlenbedingungen
    parser.add_argument("--cond_scaling", choices=["train", "legacy"], default="train",
                       help="train: MinMax über den train-Split wie im Training (Standard). "
                            "legacy: feste Bereiche (db 0-100, temperature -20-40, humidity 0-100), "
                            "damit wurden die Kennzahlen der Bachelorarbeit berechnet.")
    parser.add_argument("--train_csv", type=str, default=None,
                       help="train.csv für --cond_scaling train "
                            "(Standard: <dataset_path>/../train/train.csv)")
    return parser.parse_args()

def setup_evaluation_directories(args):
    """Setup evaluation directories and return paths dictionary."""
    eval_dir = os.path.join(args.output_base, args.model_type)
    
    paths = {
        'predictions': os.path.join(eval_dir, 'predictions'),
        'metrics': os.path.join(eval_dir, 'metrics'),
        'logs': os.path.join(eval_dir, 'logs')
    }
    
    for path in paths.values():
        helper.make_dir_if_not_exists(path)
        
    # Evaluation info speichern
    info = {
        'model_type': args.model_type,
        'checkpoint_path': args.checkpoint_path,
        'dataset_path': args.dataset_path,
        'conditions_used': {
            'temperature': args.use_temperature,
            'humidity': args.use_humidity,
            'db': args.use_db
        },
        'optim_step': args.optim_step,
        'image_size': args.image_size,
        'cond_scaling': args.cond_scaling
    }
    
    with open(os.path.join(eval_dir, 'evaluation_config.json'), 'w') as f:
        json.dump(info, f, indent=4)
        
    return paths

def main():
    args_cmd = parse_args()
    
    # CUDA Check
    if torch.cuda.is_available():
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA not available, using CPU")
    
    # Evaluation Verzeichnisse erstellen
    paths = setup_evaluation_directories(args_cmd)
    print(f"Setup evaluation directories at: {os.path.dirname(paths['predictions'])}")
    

    # Parameter laden
    params = helper.read_params("../params.json")["soundmap"]
    params.update({
        'n_samples': 1,
        'batch_size': 1,
        'temperature': 1,
        'img_size': args_cmd.image_size
    })

    class Args:
        def __init__(self):
            self.dataset = 'soundmap'
            self.direction = 'building2soundmap'
            self.model = 'glow_improved'
            self.do_lu = True
            self.grad_checkpoint = False
            self.n_block = params['n_block']
            self.n_flow = params['n_flow']
            self.reg_factor = 0.0001
            self.use_bmaps = False
            self.use_temperature = args_cmd.use_temperature
            self.use_humidity = args_cmd.use_humidity
            self.use_db = args_cmd.use_db
            self.exp = False
            self.last_optim_step = args_cmd.optim_step

    args = Args()

    # Print configuration
    print("\nEvaluation Configuration:")
    print(f"Model type: {args_cmd.model_type}")
    print(f"Flow steps: {params['n_flow']}")
    print(f"Blocks: {params['n_block']}")
    print(f"Image size: {params['img_size']}")
    print("\nExtra Conditions:")
    print(f"Temperature: {args.use_temperature}")
    print(f"Humidity: {args.use_humidity}")
    print(f"DB: {args.use_db}")

    # Model initialization
    try:
        print("\nInitializing model...")
        model = models.init_model(args, params)
        print(f"Loading checkpoint from step {args.last_optim_step}...")
        checkpoint = helper.load_checkpoint(args_cmd.checkpoint_path, args.last_optim_step, model, None, resume_train=False)
        model = checkpoint[0] if isinstance(checkpoint, tuple) else checkpoint
        model.eval()
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error during model initialization: {str(e)}")
        raise

    # Dataset laden
    try:
        print("\nLoading test dataset...")
        test_csv = pd.read_csv(os.path.join(args_cmd.dataset_path, "test.csv"))
        required_columns = ['osm']
        if args.use_db: required_columns.append('db')
        if args.use_temperature: required_columns.append('temperature')
        if args.use_humidity: required_columns.append('humidity')
        
        missing_columns = [col for col in required_columns if col not in test_csv.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        print(f"Loaded {len(test_csv)} test samples")
    except Exception as e:
        print(f"Error loading test dataset: {str(e)}")
        raise

    # Transform und Scaler Setup
    transform = transforms.Compose([
        transforms.Resize(params['img_size']),
        transforms.Grayscale(num_output_channels=1),
        transforms.ToTensor(),
    ])

    # Scaler für die Zahlenbedingungen (Reihenfolge wie im Training: db, temperature, humidity)
    cond_cols = []
    if args.use_db: cond_cols.append('db')
    if args.use_temperature: cond_cols.append('temperature')
    if args.use_humidity: cond_cols.append('humidity')

    scaler = None
    if cond_cols:
        if args_cmd.cond_scaling == 'legacy':
            # Feste Bereiche, so wurden die Kennzahlen der Bachelorarbeit berechnet.
            # Weicht vom Training ab (dort konstant 95 dB -> 0, combined: Bereiche des train-Splits).
            legacy = {'db': (0, 100), 'temperature': (-20, 40), 'humidity': (0, 100)}
            scaler = MinMaxScaler().fit(np.array([[legacy[c][0] for c in cond_cols],
                                                  [legacy[c][1] for c in cond_cols]], dtype=float))
        else:
            # Wie data_handler/soundmap/loader.py im Training: MinMaxScaler über den train-Split
            train_csv = args_cmd.train_csv or os.path.join(
                os.path.dirname(os.path.normpath(args_cmd.dataset_path)), 'train', 'train.csv')
            train_df = pd.read_csv(train_csv)
            train_vals = np.column_stack([
                train_df['db'].apply(lambda x: eval(x)['lwd500']).astype(float) if c == 'db'
                else train_df[c].astype(float)
                for c in cond_cols])
            scaler = MinMaxScaler().fit(train_vals)
        print(f"\nCondition scaling: {args_cmd.cond_scaling} {cond_cols}")
        print(f"Min: {scaler.data_min_}  Max: {scaler.data_max_}")

    # Processing statistics
    total_samples = len(test_csv)
    successful = 0
    failed = 0
    error_log = []
    
    # Create CSV file for runtime tracking
    runtime_csv_path = os.path.join(paths['metrics'], "inference_times.csv")
    with open(runtime_csv_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['sample_id', 'osm_file', 'inference_time', 'status'])

    # Main processing loop
    print("\nStarting prediction generation...")
    with torch.no_grad():
        for idx, row in tqdm(test_csv.iterrows(), total=total_samples, desc="Generating predictions"):
            try:
                # Prepare batch dictionary
                batch = {}
                
                # Load and validate building image
                building_filename = os.path.basename(row['osm'])
                building_path = os.path.join(args_cmd.dataset_path, "buildings", building_filename)
                
                if not os.path.exists(building_path):
                    raise FileNotFoundError(f"Building file not found: {building_path}")
                    
                # Process building image
                building = transform(Image.open(building_path))
                if building.size(0) == 1:
                    building = building.repeat(3, 1, 1)
                building = building.unsqueeze(0).to(device)
                batch['building'] = building
                
                # Process extra conditions
                extra_cond_values = []
                if cond_cols:
                    raw_values = []
                    for c in cond_cols:
                        if c == 'db':
                            try:
                                raw_values.append(float(eval(row['db'])['lwd500']))
                            except (KeyError, SyntaxError) as e:
                                raise ValueError(f"Invalid dB value format: {e}")
                        else:
                            raw_values.append(float(row[c]))
                    extra_cond_values = scaler.transform(np.array([raw_values]))[0].tolist()

                if extra_cond_values:
                    batch['extra_cond'] = torch.tensor(extra_cond_values, dtype=torch.float32).to(device)
                
                # Inference und Zeitmessung
                start_time = time.time()
                sampled_images = models.take_samples(
                    args,
                    params,
                    model,
                    batch['building'],
                    batch,
                    n_samples=1
                )
                inference_time = time.time() - start_time
                
                # Validate generated image
                if torch.isnan(sampled_images).any():
                    raise ValueError("Generated image contains NaN values")
                
                # Save the generated image
                utils.save_image(
                    sampled_images[0],
                    os.path.join(paths['predictions'], f"y_{idx}.png"),
                    normalize=False
                )
                
                # Log successful inference time
                with open(runtime_csv_path, 'a', newline='') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([idx, building_filename, inference_time, 'success'])
                
                successful += 1
                
                # Memory management
                if idx % 50 == 0:
                    torch.cuda.empty_cache()
                
            except Exception as e:
                failed += 1
                error_msg = f"Error processing sample {idx}: {str(e)}"
                error_log.append(error_msg)
                print(f"\n{error_msg}")
                
                # Log failed inference
                with open(runtime_csv_path, 'a', newline='') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([idx, building_filename, -1, 'failed'])
                continue

    # Analyze runtime data
    runtime_df = pd.read_csv(runtime_csv_path)
    successful_times = runtime_df[runtime_df['status'] == 'success']['inference_time']

    # Performance statistics
    print("\nEvaluation complete:")
    print(f"Total samples: {total_samples}")
    print(f"Successfully processed: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(successful/total_samples)*100:.2f}%")
    
    if len(successful_times) > 0:
        stats = {
            "average_inference_time": float(successful_times.mean()),
            "median_inference_time": float(successful_times.median()),
            "min_inference_time": float(successful_times.min()),
            "max_inference_time": float(successful_times.max()),
            "total_inference_time": float(successful_times.sum()),
            "success_rate": float((successful/total_samples)*100),
            "total_samples": int(total_samples),
            "successful_samples": int(successful),
            "failed_samples": int(failed)
        }
        
        print("\nInference Time Statistics:")
        print(f"Average inference time: {stats['average_inference_time']:.4f} seconds")
        print(f"Median inference time: {stats['median_inference_time']:.4f} seconds")
        print(f"Min inference time: {stats['min_inference_time']:.4f} seconds")
        print(f"Max inference time: {stats['max_inference_time']:.4f} seconds")
        print(f"Total inference time: {stats['total_inference_time']:.2f} seconds")
        
        # Save statistics
        with open(os.path.join(paths['metrics'], 'performance_statistics.json'), 'w') as f:
            json.dump(stats, f, indent=4)
    
    # Save error log if any errors occurred
    if error_log:
        error_log_path = os.path.join(paths['logs'], "error_log.txt")
        with open(error_log_path, 'w') as f:
            f.write("\n".join(error_log))
        print(f"\nError log saved to: {error_log_path}")

    print(f"\nEvaluation results saved to: {os.path.dirname(paths['predictions'])}")

if __name__ == "__main__":
    main()