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
        dict: Dictionary containing allergens and macronutrients info
    """

    try:
        prompt = f"""

            Given the following ingredients: {', '.join(ingredients)},
            Analyze and provide:
            1. Allergens: List of common allergens based on the ingredients. (e.g., "Gluten", "Dairy", "Nuts", "Eggs", "Soy", "Shellfish", etc.)
            2. Macronutrients: Provide estimated value in the exact format "Xg protein, Xg fat"  (e.g., "Calories", "Fat", "Carbohydrates", "Protein", etc.)
            
            Respond in valid JSON format:
            {{
                "allergens": ["Gluten", "Dairy", "Nuts", "Eggs", "Soy", "Shellfish", etc.],
                "macronutrients": "22g protein, 12g fat"
            }}

            Important:
            1. Allergens should be based on ingredients.
            2. Macronutrients should be in display format with "g" units.
            3. Provide realistic estimates for a typical serving size.
            """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )

        content = response.choices[0].message.content

        try:
            nutrition_data = json.loads(content)
            return nutrition_data
        except json.JSONDecodeError as e:
            return {
                "allergens": [],
                "macronutrients": "",
                "raw_response": content,
                "error": str(e),
            }
    except Exception as e:
        return {"allergens": [], "macronutrients": "", "error": str(e)}
