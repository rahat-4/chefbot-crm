import json
import re
from typing import Dict, List, Union

from openai import OpenAI


def generate_nutrition_info(ingredients: List[str], client: OpenAI) -> Dict:
    """
    Generate nutrition information for given ingredients with quantities using OpenAI API

    Args:
        ingredients (list): List of ingredients with quantities, e.g., ["milk (500ml)", "onion (200g)"]

    Returns:
        dict: Dictionary containing allergens and macronutrients info with units
    """

    try:
        # Validate input
        if not ingredients or not isinstance(ingredients, list):
            return {
                "allergens": [],
                "macronutrients": {},
                "error": "Invalid or empty ingredients list",
            }

        # Extract total weight/portion info for better accuracy
        ingredients_text = ", ".join(ingredients)

        prompt = f""" 
        You are a professional nutritionist. Analyze these EXACT ingredients with their specified quantities: {ingredients_text}
        
        Calculate nutrition information for the TOTAL recipe made from ALL these ingredients combined (not per 100g).
        
        Tasks:
        1. Allergens: List all allergens present in these specific ingredients
        2. Macronutrients: Calculate nutritional values for the entire dish made from these exact quantities
        
        IMPORTANT CALCULATION RULES:
        - Use the EXACT quantities provided (e.g., if 500ml milk + 200g onion, calculate for that total amount)
        - Sum up nutrients from ALL ingredients to get total dish nutrition
        - Be precise with quantities - don't estimate "typical servings"
        - Include significant nutrients based on the actual ingredients and amounts
        
        Common allergens to check: milk/dairy, eggs, gluten/wheat, nuts, soy, shellfish, fish, sesame
        
        Respond in this EXACT JSON format (numbers only, no units in values):
        {{
            "allergens": ["list actual allergens found"],
            "macronutrients": {{
                "calories": numeric_value_in_kcal,
                "protein": numeric_value_in_grams,
                "carbohydrates": numeric_value_in_grams,
                "fat": numeric_value_in_grams,
                "fiber": numeric_value_in_grams,
                "sugar": numeric_value_in_grams,
                "sodium": numeric_value_in_mg,
                "vitamin_c": numeric_value_in_mg,
                "calcium": numeric_value_in_mg,
                "iron": numeric_value_in_mg,
                "potassium": numeric_value_in_mg
            }}
        }}
        
        CRITICAL: 
        - Only numeric values in macronutrients (no "g", "mg", "kcal" in the JSON)
        - Only include allergens actually present in the ingredients
        - Calculate for the TOTAL recipe, not per serving or per 100g
        - If a nutrient is negligible, set to 0
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert nutritionist with access to comprehensive food databases. Provide precise calculations based on exact ingredient quantities.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=600,  # Slightly more tokens for complex calculations
        )

        content = response.choices[0].message.content
        match = re.search(r"(\{.*\})", content, re.DOTALL)

        try:
            json_str = match.group(1)
            nutrition_data = json.loads(json_str)

            # Validate the response structure
            required_keys = ["allergens", "macronutrients"]
            for key in required_keys:
                if key not in nutrition_data:
                    raise ValueError(f"Missing required key: {key}")

            # Validate allergens
            allergens = nutrition_data["allergens"]
            if not isinstance(allergens, list):
                raise ValueError("Allergens must be a list")

            # Validate and process macronutrients
            macros = nutrition_data["macronutrients"]
            if not isinstance(macros, dict):
                raise ValueError("Macronutrients must be a dictionary")

            # Define unit mapping for different nutrients
            unit_mapping = {
                "calories": "kcal",
                "protein": "g",
                "carbohydrates": "g",
                "fat": "g",
                "fiber": "g",
                "sugar": "g",
                "sodium": "mg",
                "vitamin_c": "mg",
                "calcium": "mg",
                "iron": "mg",
                "potassium": "mg",
                "magnesium": "mg",
                "zinc": "mg",
                "vitamin_a": "µg",
                "vitamin_d": "µg",
                "vitamin_e": "mg",
                "vitamin_k": "µg",
                "folate": "µg",
                "vitamin_b12": "µg",
                "phosphorus": "mg",
                "saturated_fat": "g",
                "cholesterol": "mg",
            }

            # Process macronutrients - ensure numeric and add units
            processed_macros = {}
            for key, value in macros.items():
                try:
                    # Clean any existing units and convert to numeric
                    if isinstance(value, str):
                        # Remove common units that might be in the response
                        cleaned_value = re.sub(r"[a-zA-Zµ]+", "", str(value)).strip()
                        numeric_value = (
                            float(cleaned_value)
                            if "." in cleaned_value
                            else int(float(cleaned_value))
                        )
                    else:
                        numeric_value = (
                            float(value) if isinstance(value, (int, float)) else 0
                        )

                    # Round to reasonable decimal places
                    if numeric_value == int(numeric_value):
                        numeric_value = int(numeric_value)
                    else:
                        numeric_value = round(numeric_value, 2)

                    # Add appropriate unit
                    unit = unit_mapping.get(key.lower(), "g")
                    processed_macros[key] = f"{numeric_value}{unit}"

                except (ValueError, TypeError) as e:
                    print(f"Error processing nutrient {key}: {e}")
                    # Set default value with unit
                    unit = unit_mapping.get(key.lower(), "g")
                    processed_macros[key] = f"0{unit}"

            nutrition_data["macronutrients"] = processed_macros

            # Additional validation - ensure we have basic nutrients
            essential_nutrients = ["calories", "protein", "carbohydrates", "fat"]
            for nutrient in essential_nutrients:
                if nutrient not in processed_macros:
                    unit = unit_mapping.get(nutrient, "g")
                    processed_macros[nutrient] = f"0{unit}"

            print(f"Nutrition ---------------------data: {nutrition_data}")

            return nutrition_data

        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw response: {content}")
            return {
                "allergens": [],
                "macronutrients": {
                    "calories": "0kcal",
                    "protein": "0g",
                    "carbohydrates": "0g",
                    "fat": "0g",
                },
                "raw_response": content,
                "error": f"Parsing error: {str(e)}",
            }

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return {
            "allergens": [],
            "macronutrients": {
                "calories": "0kcal",
                "protein": "0g",
                "carbohydrates": "0g",
                "fat": "0g",
            },
            "error": f"API error: {str(e)}",
        }
