import json
from datetime import datetime
from random import randint
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404

from Course.models import Course
from Review.models import Review, ReviewEvaluation
from Elaboration.models import Elaboration
from Challenge.models import Challenge
from ReviewQuestion.models import ReviewQuestion
from ReviewAnswer.models import ReviewAnswer
from Notification.models import Notification
from Review.models import ReviewConfig


def create_context_review(request):
    data = {}
    if 'id' in request.GET:
        user = RequestContext(request)['user']
        challenge = Challenge.objects.get(pk=request.GET.get('id'))
        if not challenge.is_enabled_for_user(user):
            raise Http404
        if challenge.has_enough_user_reviews(user):
            raise Http404
        if not challenge.submitted_by_user(user):
            raise Http404
        review = Review.get_open_review(challenge, user)
        if not review:
            # number of hours needed to pass until elaboration is applicable as candidate
            offset = randint(ReviewConfig.get_candidate_offset_min(), ReviewConfig.get_candidate_offset_max())
            review_candidate = Elaboration.get_review_candidate(challenge, user, offset)
            if review_candidate:
                review = Review(elaboration=review_candidate, reviewer=user)
                review.save()
            else:
                return data
        data['review'] = review
        data['stack_id'] = challenge.get_stack().id
        review_questions = ReviewQuestion.objects.filter(challenge=challenge).order_by("order")
        data['questions'] = review_questions
    return data


@login_required()
def review(request, course_short_title):
    data = create_context_review(request)
    data['course'] = Course.get_or_raise_404(course_short_title)
    return render_to_response('review.html', data, context_instance=RequestContext(request))


@login_required()
def review_answer(request, course_short_title):
    user = RequestContext(request)['user']
    if request.POST:
        data = request.body.decode(encoding='UTF-8')
        data = json.loads(data)
        review_id = data['review_id']
        answers = data['answers']
        try:
            review = Review.objects.get(pk=review_id)
            challenge = review.elaboration.challenge
            if not challenge.is_enabled_for_user(user):
                raise Http404
            if not review == Review.get_open_review(challenge, user):
                raise Http404
        except:
            raise Http404
        review.appraisal = data['appraisal']

        for answer in answers:
            question_id = answer['question_id']
            text = answer['answer']
            review_question = ReviewQuestion.objects.get(pk=question_id)
            ReviewAnswer(review=review, review_question=review_question, text=text).save()
            # send notifications
        review.submission_time = datetime.now()
        review.save()
        try:
            if review.appraisal == review.NOTHING:
                Notification.bad_review(review)
            else:
                Notification.enough_peer_reviews(review)
        except:
            print('Could not send Notification')

    return HttpResponse()

@login_required()
def evaluate(request, course_short_title):
    user = RequestContext(request)['user']
    if not request.GET:
        raise Http404
    if not 'appraisal' in request.GET:
        raise Http404
    appraisal = request.GET['appraisal']
    if not 'review_id' in request.GET:
        raise Http404
    review_id = request.GET['review_id']
    review = Review.objects.get(id=review_id)
    review_evaluation, created = ReviewEvaluation.objects.get_or_create(user=user, review=review)
    review_evaluation.appraisal = appraisal
    review_evaluation.save()
    return HttpResponse()