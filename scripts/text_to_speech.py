import platform

def text_to_speech(text, lang='en'):
  """
  Converts text to speech using a platform-agnostic approach.

  Args:
    text: The text string to be spoken.
    lang: Language code (e.g., 'en' for English, 'fr' for French).
          The availability of languages depends on the specific TTS engine used.

  Returns:
    None. Plays the spoken text.
  """

  system = platform.system()

  if system == "Windows":
    try:
      # Windows:  Uses pyttsx3 (cross-platform, requires installation)
      import pyttsx3
      engine = pyttsx3.init()

      # Set voice based on language (optional, but can improve quality if available)
      voices = engine.getProperty('voices')
      for voice in voices:
          if lang in voice.id:  #Try to select a voice that matches the language
              engine.setProperty('voice', voice.id)
              break #stop if you find a voice that matches
      engine.say(text)
      engine.runAndWait()
      engine.stop()

    except ImportError:
      print("pyttsx3 not found. Please install it: pip install pyttsx3")
      print("Falling back to PowerShell for Text-to-Speech (Windows-specific).")
      # Windows fallback: Use PowerShell (built-in)
      try:
          import subprocess
          subprocess.run(['powershell', '-Command', f'Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}");'])
      except Exception as e:
          print(f"Error using PowerShell TTS: {e}")
          print("No TTS available on this system.")

  elif system == "Linux":
    try:
      # Linux: Uses gTTS (Google Text-to-Speech) + mpg321 or paplay/aplay
      from gtts import gTTS
      import tempfile  #For handling temporary audio files

      # Create a temporary audio file
      with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
          tts = gTTS(text=text, lang=lang)
          tts.save(temp_file.name)

          # Play the audio file using mpg321 (preferred) or paplay/aplay
          try:
              import subprocess
              subprocess.run(['mpg321', temp_file.name], check=True)  # mpg321 exits with non-zero code on error
          except (subprocess.CalledProcessError, FileNotFoundError):
              try:  #Try paplay
                  subprocess.run(['paplay', temp_file.name], check=True)
              except (subprocess.CalledProcessError, FileNotFoundError):
                  try: #Try aplay
                      subprocess.run(['aplay', temp_file.name], check=True)
                  except (subprocess.CalledProcessError, FileNotFoundError):
                      print("mpg321, paplay, and aplay not found. Please install one (e.g., 'sudo apt-get install mpg321').")

    except ImportError:
      print("gTTS not found. Please install it: pip install gTTS")
    except Exception as e:
      print(f"Error using gTTS: {e}")
  else:
    print(f"Text-to-speech not implemented for operating system: {system}")


# Example usage:
if __name__ == "__main__":
    my_text = "Hello, this is a test of the text-to-speech function."
    text_to_speech(my_text)

    my_french_text = "Bonjour, c'est un test de la fonction de synthèse vocale."
    text_to_speech(my_french_text, lang='fr') # Use French

