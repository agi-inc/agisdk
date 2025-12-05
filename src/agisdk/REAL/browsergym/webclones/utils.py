import os

from openai import OpenAI


async def scrape_content(page):
    # Evaluate JavaScript to extract the content inside the <pre> tag within the #__next div
    content = await page.evaluate("""() => {
        const nextDiv = document.querySelector('#__next');
        const preTag = nextDiv ? nextDiv.querySelector('pre') : null;
        return preTag ? preTag.innerText : "No <pre> tag found.";
    }""")

    print(content)


def generate_from_model(model: str = "gpt4o", prompt: str = ""):
    client = OpenAI()
    os.getenv("OPENAI_API_KEY")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
