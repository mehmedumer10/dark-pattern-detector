import os
import shutil
import json
from pathlib import Path

class DarkPatternDatasetSeparator:
    def __init__(self, base_dir):
        """
        Initialize the separator with the base directory path
        
        Args:
            base_dir: Path to the output folder (path/to/dataset/output)
        """
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / 'images'
        self.annotations_dir = self.base_dir / 'annotations'
        
        # Create output directories
        self.output_base = self.base_dir / 'separated_datasets'
        self.web_dir = self.output_base / 'web'
        self.app_dir = self.output_base / 'app'
        self.mobile_dir = self.output_base / 'mobile'
        
        # Create subdirectories for images and annotations
        for category_dir in [self.web_dir, self.app_dir, self.mobile_dir]:
            (category_dir / 'images').mkdir(parents=True, exist_ok=True)
            (category_dir / 'annotations').mkdir(parents=True, exist_ok=True)
    
    def detect_category_from_filename(self, filename):
        """
        Detect category based on filename patterns
        
        Args:
            filename: Name of the image or annotation file
            
        Returns:
            str: 'web', 'app', or 'mobile'
        """
        filename_lower = filename.lower()
        
        # Pattern matching for web-based
        web_patterns = ['web', 'website', 'browser', 'desktop', 'www']
        for pattern in web_patterns:
            if pattern in filename_lower:
                return 'web'
        
        # Pattern matching for app-based
        app_patterns = ['app', 'application', 'software', 'desktop_app']
        for pattern in app_patterns:
            if pattern in filename_lower:
                return 'app'
        
        # Pattern matching for mobile-based
        mobile_patterns = ['mobile', 'phone', 'android', 'ios', 'iphone', 'smartphone']
        for pattern in mobile_patterns:
            if pattern in filename_lower:
                return 'mobile'
        
        # If no pattern matches, try to infer from content (for annotations)
        return None
    
    def analyze_annotation_content(self, annotation_path):
        """
        Analyze JSON annotation content to detect category
        
        Args:
            annotation_path: Path to annotation JSON file
            
        Returns:
            str: 'web', 'app', or 'mobile' based on content
        """
        try:
            with open(annotation_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if annotation contains category information
            if isinstance(data, dict):
                # Look for category in various possible fields
                for field in ['category', 'type', 'platform', 'source', 'context']:
                    if field in data:
                        value = str(data[field]).lower()
                        if 'web' in value:
                            return 'web'
                        elif 'app' in value or 'application' in value:
                            return 'app'
                        elif 'mobile' in value or 'phone' in value or 'ios' in value or 'android' in value:
                            return 'mobile'
                
                # Check image filename in annotation
                for field in ['image_path', 'filename', 'image_name', 'file_name']:
                    if field in data:
                        result = self.detect_category_from_filename(data[field])
                        if result:
                            return result
            
            # Check metadata if exists
            if isinstance(data, dict) and 'metadata' in data:
                metadata_str = json.dumps(data['metadata']).lower()
                if 'web' in metadata_str:
                    return 'web'
                elif 'app' in metadata_str:
                    return 'app'
                elif 'mobile' in metadata_str:
                    return 'mobile'
                    
        except Exception as e:
            print(f"Error reading {annotation_path}: {e}")
        
        return None
    
    def separate_dataset(self):
        """
        Main function to separate the dataset into web, app, and mobile categories
        """
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = [f for f in os.listdir(self.images_dir) 
                      if Path(f).suffix.lower() in image_extensions]
        
        print(f"Found {len(image_files)} images to process")
        
        # Statistics
        stats = {
            'web': {'images': 0, 'annotations': 0},
            'app': {'images': 0, 'annotations': 0},
            'mobile': {'images': 0, 'annotations': 0},
            'uncategorized': []
        }
        
        # Process each image
        for image_file in image_files:
            image_path = self.images_dir / image_file
            image_stem = Path(image_file).stem
            
            # Find corresponding annotation file
            annotation_extensions = ['.json', '.xml', '.txt']
            annotation_file = None
            
            for ext in annotation_extensions:
                potential_ann = self.annotations_dir / f"{image_stem}{ext}"
                if potential_ann.exists():
                    annotation_file = potential_ann
                    break
            
            # Determine category
            category = self.detect_category_from_filename(image_file)
            
            # If not detected from filename, try annotation content
            if not category and annotation_file:
                category = self.analyze_annotation_content(annotation_file)
            
            # If still no category, try to infer from directory structure if any
            if not category:
                # Check if images are organized in subfolders
                if 'web' in str(image_path).lower():
                    category = 'web'
                elif 'app' in str(image_path).lower():
                    category = 'app'
                elif 'mobile' in str(image_path).lower():
                    category = 'mobile'
            
            # Copy/move files to respective directories
            if category and category in ['web', 'app', 'mobile']:
                # Copy image
                dest_image_dir = self.output_base / category / 'images'
                dest_image_path = dest_image_dir / image_file
                shutil.copy2(image_path, dest_image_path)
                stats[category]['images'] += 1
                
                # Copy annotation if exists
                if annotation_file:
                    dest_ann_dir = self.output_base / category / 'annotations'
                    dest_ann_path = dest_ann_dir / annotation_file.name
                    shutil.copy2(annotation_file, dest_ann_path)
                    stats[category]['annotations'] += 1
                
                print(f"✓ {image_file} → {category}")
            else:
                stats['uncategorized'].append(image_file)
                print(f"? {image_file} → UNCATEGORIZED")
        
        # Also process any annotation files that don't have corresponding images
        annotation_files = [f for f in os.listdir(self.annotations_dir) 
                           if f.endswith(('.json', '.xml', '.txt'))]
        
        for ann_file in annotation_files:
            ann_path = self.annotations_dir / ann_file
            ann_stem = Path(ann_file).stem
            
            # Check if corresponding image exists
            image_exists = False
            for ext in image_extensions:
                if (self.images_dir / f"{ann_stem}{ext}").exists():
                    image_exists = True
                    break
            
            if not image_exists:
                # Try to categorize based on annotation content
                category = self.analyze_annotation_content(ann_path)
                if category and category in ['web', 'app', 'mobile']:
                    dest_ann_dir = self.output_base / category / 'annotations'
                    dest_ann_path = dest_ann_dir / ann_file
                    shutil.copy2(ann_path, dest_ann_path)
                    stats[category]['annotations'] += 1
                    print(f"✓ {ann_file} (orphan) → {category}")
        
        # Print summary
        print("\n" + "="*50)
        print("DATASET SEPARATION COMPLETE!")
        print("="*50)
        print(f"\nWeb-based: {stats['web']['images']} images, {stats['web']['annotations']} annotations")
        print(f"App-based: {stats['app']['images']} images, {stats['app']['annotations']} annotations")
        print(f"Mobile-based: {stats['mobile']['images']} images, {stats['mobile']['annotations']} annotations")
        print(f"\nUncategorized: {len(stats['uncategorized'])} files")
        
        if stats['uncategorized']:
            print("\nUncategorized files:")
            for f in stats['uncategorized']:
                print(f"  - {f}")
        
        print(f"\nOutput directories created at: {self.output_base}")
        print("\nDirectory structure:")
        print(f"  {self.output_base}/")
        print(f"    ├── web/")
        print(f"    │   ├── images/")
        print(f"    │   └── annotations/")
        print(f"    ├── app/")
        print(f"    │   ├── images/")
        print(f"    │   └── annotations/")
        print(f"    └── mobile/")
        print(f"        ├── images/")
        print(f"        └── annotations/")
        
        return stats

def main():
    # Set your base directory path
    base_directory = r"path/to/dataset/output"
    
    # Create separator instance
    separator = DarkPatternDatasetSeparator(base_directory)
    
    # Run separation
    stats = separator.separate_dataset()
    
    # Optional: Create a summary report
    report_path = separator.output_base / 'separation_report.txt'
    with open(report_path, 'w') as f:
        f.write("Dark Pattern Dataset Separation Report\n")
        f.write("="*40 + "\n\n")
        f.write(f"Web-based: {stats['web']['images']} images, {stats['web']['annotations']} annotations\n")
        f.write(f"App-based: {stats['app']['images']} images, {stats['app']['annotations']} annotations\n")
        f.write(f"Mobile-based: {stats['mobile']['images']} images, {stats['mobile']['annotations']} annotations\n")
        f.write(f"\nUncategorized: {len(stats['uncategorized'])} files\n")
        
        if stats['uncategorized']:
            f.write("\nUncategorized files:\n")
            for file in stats['uncategorized']:
                f.write(f"  - {file}\n")
    
    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    main()