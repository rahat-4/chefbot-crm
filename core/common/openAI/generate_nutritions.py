import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API"))


def generate_nutrition_info(ingredients: list) -> dict:
    """
    Generate nutrition information for given ingredients using OpenAI API

    Args:
        ingredients (list): List of ingredient names

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

        prompt = f""" 
        You are a nutrition expert. Analyze the following specific ingredients: {', '.join(ingredients)}
        
        Based on these EXACT ingredients, provide:
        1. Allergens: Identify actual allergens present in these specific ingredients
        2. Macronutrients: Calculate realistic nutritional values for a typical serving made from these ingredients
        
        Include ALL relevant macronutrients that are significant in these ingredients such as:
        - Calories, Protein, Carbohydrates, Fat, Fiber, Sugar, Sodium, etc.
        - Include any vitamins, minerals, or other nutrients that are notable in these ingredients
        
        Respond in this EXACT JSON format with numeric values only:
        {{
            "allergens": ["actual allergens found in the ingredients"],
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
                "iron": numeric_value_in_mg
            }}
        }}
        
        IMPORTANT RULES:
        - Only include allergens that are actually present in the given ingredients
        - Use numeric values (integers/floats) for macronutrients, not strings with units
        - Include all relevant nutrients based on the specific ingredients provided
        - Base estimates on a realistic serving size (e.g., 100g or typical portion)
        - Analyze the ACTUAL ingredients provided, not generic examples
        - If a nutrient is not significant in the ingredients, you can omit it or set it to 0
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise nutrition analyst. Provide accurate nutritional analysis based only on the specific ingredients given.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        print(f"OpenAI Response: {content}")  # Debug log

        try:
            nutrition_data = json.loads(content)

            # Validate the response structure
            if (
                "allergens" not in nutrition_data
                or "macronutrients" not in nutrition_data
            ):
                raise ValueError("Invalid response structure")

            # Ensure macronutrients are numeric and add appropriate units
            macros = nutrition_data["macronutrients"]
            if not isinstance(macros, dict):
                raise ValueError("Macronutrients must be a dictionary")

            # Define unit mapping for different nutrients
            unit_mapping = {
                "calories": "cal",
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
            }

            # Convert all macronutrient values to proper numeric format and add units
            for key, value in macros.items():
                try:
                    # Remove common units and convert to float/int
                    cleaned_value = (
                        str(value)
                        .replace("g", "")
                        .replace("mg", "")
                        .replace("kcal", "")
                        .replace("cal", "")
                        .replace("µg", "")
                        .strip()
                    )
                    numeric_value = (
                        float(cleaned_value)
                        if "." in cleaned_value
                        else int(cleaned_value)
                    )

                    # Add appropriate unit based on nutrient type
                    unit = unit_mapping.get(key.lower(), "g")  # Default to grams
                    macros[key] = f"{numeric_value}{unit}"

                except (ValueError, TypeError):
                    # If conversion fails, set to 0 with appropriate unit
                    unit = unit_mapping.get(key.lower(), "g")
                    macros[key] = f"0{unit}"

            return nutrition_data

        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {e}")
            return {
                "allergens": [],
                "macronutrients": {},
                "raw_response": content,
                "error": str(e),
            }
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return {"allergens": [], "macronutrients": {}, "error": str(e)}
