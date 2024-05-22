# Pool Guard

This bot automatically enforces rules for sign-up at swim trainings.
It enforces the following two rules:

- If any of the Wednesday/Thursday swim trainings is full, you cannot attend both.
- If you get a spot from the waitlist, you have one hour to accept it.

The bot tries to be nice when you sign-up for multiple swim trainings and will try to delete your oldest sign-up.

## Usage

You must have [Pipenv](https://pipenv.pypa.io/en/latest/) installed to run this bot.
Start it by:

```
pipenv install
pipenv run python waitlist-guard.py --user your@mail.example --password yoursupersecretspondpassword
```

The account that is used for logging in must have administrator privileges such that it can deregister people from events who violate the rules as stated above.
