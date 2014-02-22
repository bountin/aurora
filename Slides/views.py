import datetime
from datetime import timedelta
import re
import sys

from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.timezone import utc

from Course.models import Course
from Slides.models import Lecture, Slide, Stream
from Slides.settings import LIVECAST_START

"""
- slidecasting_mode
sets the state of the contentbar (which is included in all templates 
that are used by slidecasting), it has one of the following values:
    * 'start'
    * 'livecast'
    * 'studio'
    * 'new_comments_since'
    * 'marked_slides'
    * 'exercises'
    * 'discourses'
    * 'search_results'
    * 'create_pdf'
    
- tags
the following tags can be attached to slides:
    * .preparation
    * .exercise
"""


def start(request):
    course = RequestContext(request)['last_selected_course']
    lectures = _get_contentbar_data(course)
    render_dict = {'slidecasting_mode': 'start', 'course':course, 'lectures': lectures}
    return render_to_response('start.html', render_dict, context_instance=RequestContext(request))


def livecast_new_slide(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
    except (Course.DoesNotExist, Course.MultipleObjectsReturned):
        raise Http404
    #now = datetime.datetime.now()
    #lecture_right_now = Lecture.objects.filter(course=course, start__lte=now, end__gte=now, active=True)
    if _livecast_now(course):
        return HttpResponse('lecture right now -> livecast')
    else:
        return HttpResponse('no lecture right now -> prep slides. ')


def livecast_update_slide(request, lecture_id_relative, slide_id, client_timestamp):
    # TODO
    # check for new slide
    # render marker_div
    render_dict = {}
    json_return_dict = {'hello': 'world'}
    return HttpResponse('<html><body>' + str(json_return_dict) + '</body></html>')


def livecast(request, lecture_id_relative):
    course = RequestContext(request)['last_selected_course']
    lectures = _get_contentbar_data(course)
    lecture = get_object_or_404(Lecture, course=course, active=True, id_relative=lecture_id_relative)
    if not _livecast_now(lecture):
        return redirect('studio_lecture', course_short_title=course_short_title, lecture_id_relative=lecture_id_relative)
    render_dict = {'slidecasting_mode': 'livecast', 'course':course, 'lectures': lectures, 'lecture': lecture }
    return render_to_response('livecast.html', render_dict, context_instance=RequestContext(request))


def studio_lecture(request, lecture_id_relative):
    course = RequestContext(request)['last_selected_course']
    lectures = _get_contentbar_data(course)
    lecture = get_object_or_404(Lecture, course=course, active=True, id_relative=lecture_id_relative)
    if _livecast_now(lecture):
        return redirect('livecast', lecture_id_relative=lecture_id_relative)
    slides = Slide.objects.filter(lecture=lecture)
    slides = _cache_slide_markers(slides)
    slides_preparation = slides.filter(tags__contains='.preparation')
    slides_preparation = _cache_slide_markers(slides_preparation)
    videoclip_url, videoclip_name = _get_videoclip_url_name(lecture)
    videoclip_chapters = _get_videoclip_chapters(lecture, slides, slides_preparation)
    
    render_dict = {'slidecasting_mode': 'studio', 'course':course, 'lectures': lectures, 'lecture': lecture, 'slides': slides} 
    render_dict.update({ 'videoclip_name': videoclip_name, 'videoclip_url': videoclip_url, 'videoclip_chapters': videoclip_chapters })
    return render_to_response('studio.html', render_dict, context_instance=RequestContext(request))
    

def studio_marker(request, marker):
    course = RequestContext(request)['last_selected_course']
    lectures = _get_contentbar_data(course)
    if marker == 'confusing':
        slides = Slide.objects.filter(confusing=request.user.customuser, lecture__course__short_title=course_short_title)
    elif marker == 'important':
        slides = Slide.objects.filter(important=request.user.customuser, lecture__course__short_title=course_short_title)
    elif marker == 'liked':
        slides = Slide.objects.filter(liked=request.user.customuser, lecture__course__short_title=course_short_title)
    slides = _cache_slide_markers(slides)
    render_dict = {'slidecasting_mode': 'marked_slides', 'marker': marker, 'course':course, 'lectures': lectures, 'slides': slides}
    return render_to_response('studio.html', render_dict, context_instance=RequestContext(request))


def studio_search(request):
    course = RequestContext(request)['last_selected_course']
    lectures = _get_contentbar_data(coursee)
    search_text = request.GET.get('search_text', '')
    if search_text.strip():
        search_query = _get_query(search_text, ['title', 'tags']) # TODO: we'll need to search the comments here too.
        slides = Slide.objects.filter(lecture__course__short_title=course_short_title).filter(search_query).distinct()
        slides = _cache_slide_markers(slides)
        render_dict = {'slidecasting_mode': 'search_results', 'course':course, 'lectures': lectures, 'slides': slides, 
                        'search_text': search_text}
        return render_to_response('studio.html', render_dict, context_instance=RequestContext(request))
    else:
        raise Http404


def mark_slide(request, slide_id, marker, value):
    course = RequestContext(request)['last_selected_course']
    if request.method == 'POST':
        try:
            slide = Slide.objects.get(id=slide_id)
        except (Slide.DoesNotExist, Slide.MultipleObjectsReturned): 
            return HttpResponse(simplejson.dumps({'success': False}), mimetype='application/javascript')
        if value == 'xxx':
            return HttpResponse(simplejson.dumps({'success': False}), mimetype='application/javascript')
        elif value == 'true':
            slide.set_marker(request.user.customuser, marker, True)
        else:
            slide.set_marker(request.user.customuser, marker, False)
        count = slide.get_marker_count(marker)
        new_title = render_to_string('marker_title.html', {'count': count, 'marker': marker})
        json_return_dict = {'success': True, 'count': count, 'new_title': new_title}
        return HttpResponse(simplejson.dumps(json_return_dict), mimetype='application/javascript')
    return HttpResponse(simplejson.dumps({'success': False}), mimetype='application/javascript')


def _get_contentbar_data(course):
    lectures = Lecture.objects.filter(course=course, active=True)
    return lectures


def _get_videoclip_url_name(lecture):
    try:
        return lecture.stream.url, lecture.stream.clipname
    except Stream.DoesNotExist:
        return "no_url", "no_videoclip"
        
        
def _get_videoclip_chapters(lecture, slides, slides_preparation):
    try:
        offset = lecture.stream.offset
        return [[slide.id, 1000 * ( offset + (slide.pub_date - lecture.start).seconds)] for slide in slides.exclude(id__in=slides_preparation)]
    except Stream.DoesNotExist:
        return []


def _cache_slide_markers(slides):
    # call this function after you have filtered the queryset of slides you want to display.
    # it makes annotations for markers, and prefetches the marker relations. we need
    # both everywhere, where we display slides (because we show the markers everywhere). 
    # this strongly improves performance!
    return slides.annotate(count_confusing=Count('confusing')).annotate(count_important=Count('important')).annotate(count_liked=Count('liked')).prefetch_related('confusing').prefetch_related('important').prefetch_related('liked')


def _livecast_now(lecture_or_course):
    now = datetime.datetime.now()
    if type(lecture_or_course) == Lecture:
        lecture = lecture_or_course
        lecture_livecast_start = lecture.start - timedelta(minutes=LIVECAST_START)
        if now > lecture_livecast_start and now < lecture.end:
            return True
        else:
            return False
    elif type(lecture_or_course) == Course:
        course = lecture_or_course
        lecture_right_now = Lecture.objects.filter(course=course, start__lte=now, end__gte=now, active=True)
        if lecture_right_now.count() == 1:
            return True
        else:
            return False
    else:
        return False
    

def _get_query(query_string, search_fields):
    # Returns a query, that is a combination of Q objects. That combination
    # aims to search keywords within a model by testing the given search fields.
    query = None # Query to search for every search term        
    terms = _normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query


def _normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    # Splits the query string in invidual keywords, getting rid of unecessary spaces
    #    and grouping quoted words together.
    #    Example:
    #    
    #    >>> normalize_query('  some random  words "with   quotes  " and   spaces')
    #    ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    #
    #
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]
