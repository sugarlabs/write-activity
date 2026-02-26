from transformers import pipeline

class AIFeedback:
    def __init__(self):
        self.device = 0  
        self._init_pipeline()

    def _init_pipeline(self):
        try:
            self.feedback_generator = pipeline(
                "text2text-generation",  # Using T5-style text2text generation
                model="MBZUAI/LaMini-Flan-T5-248M",
                device=self.device
            )
        except Exception as error:
            if "CUDA" in str(error):
                print("CUDA error encountered. Falling back to CPU.")
                self.device = -1
                self.feedback_generator = pipeline(
                    "text2text-generation",
                    model="MBZUAI/LaMini-Flan-T5-248M",
                    device=self.device
                )
            else:
                raise error

    def get_feedback(self, text):
        prompt = (
            "You are an expert writing instructor. Provide detailed, constructive feedback on the following writing sample and include concrete suggestions for improvement:\n"
            f"{text}"
            )
        print("[DEBUG] get_feedback prompt:", prompt)
        
        try:
            result = self.feedback_generator(
                prompt,
                max_length=200,
                do_sample=True,
                truncation=True  # Explicitly enable truncation
            )
        except Exception as error:
            return f"Error generating feedback: {error}"
        # Extract feedback portion from the generated text.
        generated = result[0]["generated_text"]
        feedback = generated.split("Feedback:")[-1].strip()
        print("[DEBUG] get_feedback: Extracted feedback:", feedback)
        return feedback
    
    def get_autocomplete(self, text):
        if len(text.strip()) < 20:
            print("[DEBUG] get_autocomplete: Not enough text to generate a continuation.")
            return "Please provide more content for autocomplete."

        prompt = (
            "You are an expert creative writer. Continue the following text in a realistic and engaging manner:\n"
            f"{text}\n"
            "Continuation:"
        )
        print("[DEBUG] get_autocomplete: Prompt:", prompt)

        try:
            result = self.feedback_generator(
                prompt,
                max_length=200,
                do_sample=True,
                truncation=True
            )
        except Exception as error:
            return f"Error generating autocomplete: {error}"

        generated = result[0]["generated_text"]
        # Extract the continuation after the prompt.
        suggestion = generated.split("Continuation:")[-1].strip()
        print("[DEBUG] get_autocomplete: Extracted suggestion:", suggestion)
        return suggestion

if __name__ == '__main__':
    sample_text = (
        "This is a sample writing text. It could be improved by adding more details "
        "and varying sentence length."
    )
    ai_fb = AIFeedback()
    print("AI Feedback:")
    print(ai_fb.get_feedback(sample_text))
    print("\nAutocomplete Suggestion:")
    print(ai_fb.get_autocomplete(sample_text))