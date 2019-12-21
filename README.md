# Calendar Contest Flask App

This application automates the annual calendar contest for [Houndhaven](https://houndhaven.org).  This contest is the second largest fundraiser of the year and helps save the lives of dogs who would otherwise perish in high kill shelters around the state of Florida.

#### About Houndhaven

Houndhaven, Inc. rescues dogs and puppies from euthanasia at kill shelters. We care for them until they can be placed in loving homes or with another rescue group. We believe that these lives are precious, and we are strictly a no kill organization.
**Our mission is life.**

### How To View:
You can see a live version of the app here:  [Houndhaven-Calendar-App](http://hh-calenar.us-east-1.elasticbeanstalk.com/)

### How to use

The application is pretty straightforward.  You are able to navigate via the nav bar to:

- Home
- Submit
- Vote
- Leaderboard

## Submit

The submission page is a 2 step process.  On page one, you are provided instructions on how to submit a photo.  When you press "Pay With Card" you will get a popup (make sure your browser accepts popups) asking for payment of $10.00.

Payment handling is done through the Stripe API.  For testing purposes you can use:

**Card Number:** 4242 4242 4242 4242

**CVC Code:** Any 3 digits

**Exp Date:** Any future date

If you would like to try other credit cards, visit the [Stripe API docs](https://stripe.com/docs/testing#cards) for alternative card numbers.

After successful payment, you will be redirected to a submission form asking for your name, email, dog's name, and to attach an image.

On submission a few things occur:
- Your form info, but not the image, are uploaded to a MySQL (RDS) database
- The image is resized using the Tinify API and both the full size image and thumbnail are uploaded to Amazon S3 for storage
- The URL to both images are stored in the SQLite database
- You are redirected to the Vote page where you can now see your submission

Through the use of session cookies, you ** should ** not (hopefully) be able to skip the payment process and go straight to the submission form.

## Vote

The vote page dynamically lays out all submitted dogs in a table format.  Each row displays a thumbnail image, the dog's name, and how many votes that dog has.  There is also a button on each row allowing you to vote for that dog.  There is not currently any functionality that will allow you to vote for multiple dogs at once.
If you click on a thumbnail, a full size lightbox image is displayed so you can better see the dog you're interested in.

If you wish to vote for a dog:

- Enter the amount of votes you
- Press the corresponding Vote Now button
- You will be redirected to a checkout page that confirms your choices
- If you are happy with your choices, click the "Pay With Card" button

Payment handling is done through the Stripe API.  For testing purposes you can use:

**Card Number:** 4242 4242 4242 4242

**CVC Code:** Any 3 digits

**Exp Date:** Any future date

If you would like to try other credit cards, visit the [Stripe API docs](https://stripe.com/docs/testing#cards) for alternative card numbers.

After successful payment, you will be redirected back to the voting page where you will see the vote quantity has now updated.  The database is also updated with your userid (session cookie), the dog you voted for, and how many votes you submitted.

## Leaderboard

The leaderboard page queries the database and displays the top 12 dogs ranked in descending order by the number of votes they have received.

## Developer Notes

If you wish to fork this and use the code, you'll need to add a few things.

- If you're using locally, then the settings.py file is there for you to create a .env with all of your API variables.  You can use [python-dotenv](https://pypi.org/project/python-dotenv/)
- If you're going to roll out on AWS, that's a whole different animal.  [This tutorial](https://medium.com/@rodkey/deploying-a-flask-application-on-aws-a72daba6bb80) will get you through the bulk of it.  Hang on to that .ebextensions folder.  You'll need it.
    - If you use AWS, you won't need the settings.py or .env files.  AWS has it's own way of storing environmental variables as I'm sure other PAAS do, too.

## Misc Notes

At some point, I'll loose all the cookies.  OMG so many cookies - and go for a login feature.  I'll probably add email contact and blueprints instead of one big globby app.  This app was really just a way to see if I could get something useful up and running in Flask with no experience.  It also gave me a way to learn a little AWS.