from django.test import TestCase
from Comments.models import Comment, CommentReferenceObject
from AuroraUser.models import AuroraUser
from django.utils import timezone
import Comments.views as views


def create_comment(text, author, reference_object, parent=None, visibility=Comment.PUBLIC,
                   days=0, minutes=0, seconds=0):
    """
    creates and returns a new Comment Model object that is not being persisted
    with text by author attached to reference_object

    Parameters
    ----------
    text: string
        Comment text
    author: AuroraUser
        author of the Comment
    reference_object: django.db.models.Model
        the object the Comment should be attached to
    parent: Comments.models.Comment
        parent Comment i.e. the Comment the created Comment is responding to
    days, minutes, seconds: int
        time ago this Comment has been posted
    """
    delta = timezone.timedelta(days=-days, seconds=-(minutes*60) + seconds)
    post_date = timezone.now() + delta
    comment = Comment.objects.create(text=text, author=author, parent=parent, post_date=post_date,
                                     content_object=reference_object, visibility=visibility)
    return comment


class TestSetup():
    def __init__(self, users=5, comment_no=5, thread_size=5, ref_object=None):
        if ref_object is None:
            self.ref_object = CommentReferenceObject.objects.create
        else:
            self.ref_object = ref_object

        self.ref_object = ref_object
        self.user_generator = dummy_user_generator()
        self.parents = []
        self.replies = []
        self.users = []
        self.texts = []
        self.texts.append("Actually, I think I'm beating it back with sheer willpower. (grows another lump) Oh, my.")
        self.texts.append("I wasn't scared! I was singing! I was singing my scream song. Wooaah! Wooaaooh!")
        self.texts.append("Who wants to play video games?")
        self.texts.append("If I push this button, you will both be dangerously transported into my main brain game "
                          "frame, where it is very dangerous.")
        self.texts.append("When bad things happen, I know you want to believe they are a joke, but sometimes life is \n"
                          "scary and dark. That is why we must find the light.")
        self.texts.append("BMO (phonetically spelled Beemo) is Finn and Jake's living video game console, portable\n"
                          "electrical outlet, music player, roommate, camera, alarm clock, toaster, flashlight,\n"
                          "strobe light, skateboarder, friend, soccer player, video editor, video player, tape player\n"
                          "and Chef. It makes its appearance in the title scene of the Theme Song of every episode of\n"
                          "Adventure Time, just as Finn and Jake pound their fists together. BMO is characterized as\n"
                          "a loyal, trusting, and helpful friend who is protective of Finn and Jake.")

        self.current_ref_object = self.ref_object
        self.thread_size = thread_size

        for _ in range(users):
            self.users.append(next(self.user_generator))

        self.comment_generator = create_comment_generator(self.texts, self.users, ref_object)

        for i in range(comment_no):
            comment = next(self.comment_generator)
            if i % thread_size == 0:
                print('adding new parent: ' + str(comment))
                self.parents.append(comment)
            else:
                print('adding new reply: ' + str(comment) + " to " + str(comment))
                comment.parent = self.parents[-1]
                comment.save()
                self.replies.append(comment)


def create_comment_generator(texts, users, ref_object):
    user_index = 0
    text_index = 0

    while True:
        comment = create_comment(texts[text_index], users[user_index], ref_object)
        user_index = (user_index + 1) % len(users)
        text_index = (text_index + 1) % len(texts)
        yield comment


def dummy_user_generator():
    i = 0
    while True:
        i += 1
        n = str(i)
        user = AuroraUser.objects.create(username='du'+n, first_name='first'+n,
                                         last_name='last'+n, email='du'+n+'@foo.bar')
        user.nickname = 'duni' + n
        user.password = 'dupa' + n

        yield user


class ModelMethodTests(TestCase):
    def setUp(self):
        self.user_generator = dummy_user_generator()
        self.u1 = next(self.user_generator)
        self.u1.save()
        self.u2 = next(self.user_generator)
        self.u2.save()
        self.u3 = next(self.user_generator)
        self.u3.save()
        self.s1 = next(self.user_generator)
        self.s1.is_staff = True
        self.s1.save()

        self.ref_object1 = CommentReferenceObject.objects.create(name='ref_object1')

        self.t1 = "text1"
        self.c1 = create_comment(self.t1, self.u1, self.ref_object1)
        self.rt1 = "response text1"
        self.r1 = create_comment(self.rt1, self.u2, self.ref_object1, parent=self.c1)
        self.t2 = "text2"
        self.c2 = create_comment(self.t2, self.u2, self.ref_object1)
        self.t3 = "text3"
        self.c3 = create_comment(self.t3, self.u2, self.ref_object1)
        self.rt2 = "response text2"
        self.r2 = create_comment(self.rt1, self.u1, self.ref_object1, parent=self.c3)
        self.rt3 = "response text3"
        self.r3 = create_comment(self.rt1, self.u3, self.ref_object1, parent=self.c3)
        self.t4 = "text4"
        self.c4 = create_comment(self.t4, self.u3, self.ref_object1)

        self.ref_object2 = CommentReferenceObject.objects.create(name='ref_object2')

        self.t5 = "text5"
        self.c5 = create_comment(self.t5, self.u3, self.ref_object2)
        self.rt4 = "response text4"
        self.r4 = create_comment(self.rt4, self.s1, self.ref_object2, parent=self.c5)
        self.rt5 = "response text5"
        self.r5 = create_comment(self.rt5, self.u2, self.ref_object2, parent=self.c5)

        self.ref_object3 = CommentReferenceObject.objects.create(name='ref_object3')

        self.t6 = "text6"
        self.c6 = create_comment(self.t6, self.u1, self.ref_object3)
        self.rt6 = "response text6"
        self.r6 = create_comment(self.rt6, self.u2, self.ref_object3, parent=self.c6)
        self.rt7 = "response text7"
        self.r7 = create_comment(self.rt7, self.s1, self.ref_object3, parent=self.c6)

        self.t7 = "text7"
        self.c7 = create_comment(self.t7, self.u2, self.ref_object3)
        self.rt8 = "response text8"
        self.r8 = create_comment(self.rt8, self.u3, self.ref_object3, parent=self.c7)

        self.t8 = "text8"
        self.c8 = create_comment(self.t8, self.s1, self.ref_object3)

        self.ref_object4 = CommentReferenceObject.objects.create(name='ref_object4')

        self.t9 = "text9"
        self.c9 = create_comment(self.t9, self.u2, self.ref_object4)
        self.rt10 = "response text10"
        self.r10 = create_comment(self.rt10, self.u3, self.ref_object4, parent=self.c9)
        self.rt11 = "response text11"
        self.r11 = create_comment(self.rt11, self.s1, self.ref_object4, parent=self.c9)

        self.t10 = "text10"
        self.c10 = create_comment(self.t10, self.s1, self.ref_object4)

    def test_single_tag(self):
        t11 = 'hello #Tag this is #comment #comment'
        c11 = create_comment(t11, self.s1, self.ref_object3)
        objects = Comment.objects.filter(tags__name__in=['#tag'])
        self.assertEquals(objects[0].id, c11.id)
        self.assertEquals(objects[0].text, c11.text)


class TemplateTagTests(TestCase):
    def setUp(self):
        user_generator = dummy_user_generator()
        self.u1 = next(user_generator)
        self.u1.save()
        self.u2 = next(user_generator)
        self.u2.save()
        self.u3 = next(user_generator)
        self.u3.save()

    # @staticmethod
    # def call_render(temp, context):
    #     t = Template('{% load comments %}' + temp)
    #     c = Context(context)
    #     return t.render(c)
    #
    # def no_test_render_comment_list_tag_without_parameter(self):
    #     temp = "{% render_comment_list for %}"
    #     context = {}
    #     with self.assertRaises(template.TemplateSyntaxError):
    #         self.call_render(temp, context)
    #
    # def no_test_render_comment_list_tag_without_for(self):
    #     temp = "{% render_comment_list is bar %}"
    #     context = {}
    #     with self.assertRaises(template.TemplateSyntaxError):
    #         self.call_render(temp, context)
    #
    # def test_render_comment_list_as_feed(self):
    #     ref_object = CommentReferenceObject()
    #     ref_object.save()
    #     text_c1 = "telephone booth is magic"
    #     c1 = create_comment(text_c1, self.u1, ref_object, days=5)
    #     c1.save()
    #     text_a1 = "yeah, i can even see the star dust"
    #     a1 = create_comment(text_a1, self.u2, ref_object, parent=c1, days=2)
    #     a1.save()
    #     text_a2 = "i am also like this huge fan of phone booths"
    #     a2 = create_comment(text_a2, self.u3, ref_object, parent=c1, minutes=20)
    #     a2.save()
    #     temp = "{% render_comment_list for reference %}"
    #     context = {'reference': ref_object}
    #     rendered = self.call_render(temp, context)
    #     print(rendered)
    #     self.assertTrue(text_c1 in rendered)
    #     self.assertTrue(text_a1 in rendered)
    #     self.assertTrue(text_a2 in rendered)


class PersistentTestData:
    """
    for playing around in the shell
    """
    def __init__(self):
        self.user_generator = dummy_user_generator()

        self.u1 = next(self.user_generator)
        self.u1.save()
        self.u2 = next(self.user_generator)
        self.u2.save()
        self.u3 = next(self.user_generator)
        self.u3.save()

        self.ref_object = CommentReferenceObject()
        self.ref_object.save()
        self.text_c1 = "telephone booth is magic"
        self.c1 = create_comment(self.text_c1, self.u1, self.ref_object, days=5)
        self.c1.save()
        self.text_a1 = "yeah, i can even see the star dust"
        self.a1 = create_comment(self.text_a1, self.u2, self.ref_object, parent=self.c1, days=2)
        self.a1.save()
        self.text_a2 = "i am also like this huge fan of phone booths"
        self.a2 = create_comment(self.text_a2, self.u3, self.ref_object, parent=self.c1, minutes=20)
        self.a2.save()
        self.temp = "{% render_comment_list for reference %}"
        self.context = {'reference': self.ref_object}
        self.rendered = TagTests.call_render(self.temp, self.context)
