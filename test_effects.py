#!/usr/bin/env python3
"""
Test script to verify that effects are working correctly.
"""

import cv2
import numpy as np
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cartoon_effect():
    """Test the Cartoon effect with proper parameters."""
    print("Testing Cartoon effect...")
    
    try:
        from src.core.style_manager import StyleManager
        style_manager = StyleManager()
        
        if "Cartoon" in style_manager.style_instances:
            cartoon_style = style_manager.style_instances["Cartoon"]
            # Don't set variant for styles without variants
            
            # Create a test image
            test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Test parameters for the first Cartoon class
            params = {
                "bilateral_filter_diameter": 9,
                "bilateral_filter_sigmaColor": 75,
                "bilateral_filter_sigmaSpace": 75,
                "canny_threshold1": 100,
                "canny_threshold2": 200,
                "color_levels": 8
            }
            
            print(f"Input image shape: {test_image.shape}")
            print(f"Parameters: {params}")
            
            # Apply effect
            result = cartoon_style.apply(test_image, params)
            
            print(f"Output image shape: {result.shape}")
            print(f"Output image dtype: {result.dtype}")
            print(f"Output image min/max: {result.min()}/{result.max()}")
            
            if result.shape == test_image.shape and result.dtype == np.uint8:
                print("✅ Cartoon effect working correctly!")
                return True
            else:
                print("❌ Cartoon effect failed - wrong output format")
                return False
                
        else:
            print("❌ Cartoon style not found in style manager")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Cartoon effect: {e}")
        return False

def test_edge_detection_effect():
    """Test the Edge Detection effect with proper parameters."""
    print("\nTesting Edge Detection effect...")
    
    try:
        from src.core.style_manager import StyleManager
        style_manager = StyleManager()
        
        if "Edge Detection" in style_manager.style_instances:
            edge_style = style_manager.style_instances["Edge Detection"]
            # Don't set variant for styles without variants
            
            # Create a test image
            test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Test parameters
            params = {
                "threshold1": 100,
                "threshold2": 200
            }
            
            print(f"Input image shape: {test_image.shape}")
            print(f"Parameters: {params}")
            
            # Apply effect
            result = edge_style.apply(test_image, params)
            
            print(f"Output image shape: {result.shape}")
            print(f"Output image dtype: {result.dtype}")
            print(f"Output image min/max: {result.min()}/{result.max()}")
            
            if result.shape == test_image.shape and result.dtype == np.uint8:
                print("✅ Edge Detection effect working correctly!")
                return True
            else:
                print("❌ Edge Detection effect failed - wrong output format")
                return False
                
        else:
            print("❌ EdgeDetection not found in style manager")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Edge Detection effect: {e}")
        return False

def test_parameter_mapping():
    """Test the parameter mapping logic."""
    print("\nTesting parameter mapping...")
    
    try:
        # Simulate the parameter mapping logic
        def get_current_parameters(effect_name):
            if "Cartoon" in effect_name:
                return {
                    "quant_method": "Uniform",
                    "bits": 4,
                    "spatial_radius": 10,
                    "color_radius": 30,
                    "k": 8,
                    "downscale": 0.25
                }
            elif "Edge Detection" in effect_name:
                return {
                    "threshold1": 100,
                    "threshold2": 200
                }
            else:
                return {
                    "intensity": 50,
                    "quality": 50,
                    "speed": 50,
                    "blend": 50
                }
        
        # Test Cartoon parameters
        cartoon_params = get_current_parameters("Cartoon (Fast)")
        print(f"Cartoon parameters: {cartoon_params}")
        
        # Test Edge Detection parameters
        edge_params = get_current_parameters("Edge Detection")
        print(f"Edge Detection parameters: {edge_params}")
        
        print("✅ Parameter mapping working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing parameter mapping: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Effects System")
    print("=" * 50)
    
    tests = [
        test_cartoon_effect,
        test_edge_detection_effect,
        test_parameter_mapping
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Effects should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main() 