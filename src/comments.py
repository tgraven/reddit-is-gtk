# Copyright 2016 Sam Parkinson <sam@sam.today>
#
# This file is part of Reddit is Gtk+.
#
# Reddit is Gtk+ is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Reddit is Gtk+ is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Reddit is Gtk+.  If not, see <http://www.gnu.org/licenses/>.

import json
import arrow
from gi.repository import GObject
from gi.repository import Soup
from gi.repository import Gtk

from redditisgtk.markdownpango import markdown_to_pango, SaneLabel
from redditisgtk.palettebutton import connect_palette
from redditisgtk.api import get_reddit_api
from redditisgtk.buttons import (ScoreButtonBehaviour, AuthorButtonBehaviour,
                                 TimeButtonBehaviour, SubButtonBehaviour)


class CommentsView(Gtk.ScrolledWindow):
    '''Downloads comments, shows selftext'''

    def __init__(self, post, comments=None):
        Gtk.ScrolledWindow.__init__(self)
        self.get_style_context().add_class('root-comments-view')
        self.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        self._post = post
        self._msg = None

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._box)
        self._box.show()

        self._top = _PostTopBar(self._post, hideable=False, refreshable=True,
                                show_subreddit=True)
        self._top.get_style_context().add_class('root-comments-bar')
        self._top.refresh.connect(self.__refresh_cb)
        self._box.add(self._top)
        self._top.show()

        selfpost_label = SaneLabel(
            '<big>{title}</big>\n'
            '{selftext_pango}'.format(
               selftext_pango=markdown_to_pango(post.get('selftext')),
               title=post['title']))
        selfpost_label.get_style_context().add_class('root-comments-label')
        self._box.add(selfpost_label)
        selfpost_label.show()

        self._comments = None
        if comments is not None:
            self.__message_done_cb(comments, is_full_comments=False)
        else:
            self.__refresh_cb()

    def get_link_name(self):
        return self._post['name']

    def get_header_height(self):
        return self._comments.get_allocation().y

    def __refresh_cb(self, caller=None):
        self._msg = get_reddit_api().send_request(
            'GET', self._post['permalink'], self.__message_done_cb)

    def do_unrealize(self):
        if self._msg is not None:
            get_reddit_api().cancel(self._msg)

    def __message_done_cb(self, j, is_full_comments=True):
        self._msg = None
        if self._comments is not None:
            self._box.remove(self._comments)
            self._comments.hide()
            self._comments.destroy()

        # The 1st one is just the self post
        self._comments = _CommentsView(j[1]['data']['children'], first=True,
                                       original_poster=self._post['author'],
                                       is_full_comments=is_full_comments)
        self._comments.refresh.connect(self.__refresh_cb)
        self._box.add(self._comments)
        self._comments.show()

class _CommentsView(Gtk.ListBox):
    '''
    Actually holds the comments

    This is recursive, eg, like:

    _CommentsView
        | CommentRow
        |   | _CommentsView
        |   |   | CommentRow
        | CommentRow
    '''

    refresh = GObject.Signal('refresh')

    def __init__(self, data, first=False, depth=0, original_poster=None,
                 is_full_comments=True):
        Gtk.ListBox.__init__(self)
        self._is_first = first
        self._original_poster = original_poster
        self._depth = depth

        ctx = self.get_style_context()
        ctx.add_class('comments-view')
        if self._is_first:
            ctx.add_class('first')
        ctx.add_class('depth-{}'.format(depth % 5))

        if not is_full_comments:
            row = LoadFullCommentsRow()
            row.refresh.connect(self.__refresh_cb)
            self.insert(row, -1)
            row.show()
        self._add_comments(data)

    def _add_comments(self, data):
        for comment in data:
            comment_data = comment['data']
            row = CommentRow(comment_data, self._depth,
                             original_poster=self._original_poster)
            row.refresh.connect(self.__refresh_cb)
            row.got_more_comments.connect(self.__got_more_comments_cb)
            self.insert(row, -1)
            row.show()

    def do_row_activated(self, row):
        if self._is_first:
            viewport = self.get_parent().get_parent()
            comments_view = viewport.get_parent()
            # Stop the kinetic scroll, otherwise it will override our
            # scrolling adjustment
            comments_view.props.kinetic_scrolling = False

            # Scroll to the top of the collapsed row
            r = row.get_allocation()
            header = comments_view.get_header_height()
            adj = viewport.get_vadjustment()
            adj.props.value = r.y + header

            comments_view.props.kinetic_scrolling = True

            row.do_activated()

    def __refresh_cb(self, caller):
        self.refresh.emit()

    def __got_more_comments_cb(self, caller_button, more_comments):
        caller_button.hide()
        self.remove(caller_button)
        caller_button.destroy()

        self._add_comments(more_comments)


class LoadFullCommentsRow(Gtk.ListBoxRow):

    refresh = GObject.Signal('refresh')

    def __init__(self):
        Gtk.ListBoxRow.__init__(self)

        bar = Gtk.InfoBar(message_type=Gtk.MessageType.QUESTION)
        bar.connect('response', self.__response_cb)
        label = Gtk.Label(label='Showing only a subset of comments')
        bar.get_content_area().add(label)
        label.show()

        bar.add_button('Show All Comments', 1)
        self.add(bar)
        bar.show()

    def __response_cb(self, button, response):
        self.refresh.emit()

    def do_activated(self):
        self.refresh.emit()


class _PostTopBar(Gtk.Bin):

    hide_toggled = GObject.Signal('hide-toggled', arg_types=[bool])
    refresh = GObject.Signal('refresh')

    def __init__(self, data, hideable=True, pm=False, original_poster=None,
                 refreshable=False, show_subreddit=False):
        Gtk.Bin.__init__(self)
        self.data = data

        self._b = Gtk.Builder.new_from_resource(
            '/today/sam/reddit-is-gtk/post-top-bar.ui')
        self.add(self._b.get_object('box'))
        self.get_child().show()

        self.expand = self._b.get_object('expand')
        self.expand.props.visible = hideable
        self._b.get_object('pm').props.visible = pm
        self._b.get_object('refresh').props.visible = refreshable

        self._favorite = self._b.get_object('favorite')
        self._favorite.props.visible= 'saved' in self.data
        self._favorite.props.active = self.data.get('saved')

        self._read = self._b.get_object('unread')
        self._read.props.visible = 'new' in data
        if 'new' in data:
            if data['new']:
                self._read.props.active = False
                self._read.get_style_context().add_class('unread')
                self._read.props.label = 'Mark as Read'
            else:
                self._read.props.active = True
                self._read.props.sensitive = False
                self._read.props.label = 'Read'

        self._name_button = self._b.get_object('name')
        self._abb = AuthorButtonBehaviour(self._name_button, self.data,
                                          original_poster)

        self._score_button = self._b.get_object('score')
        self._score_button.props.visible = 'score' in data
        if 'score' in data:
            self._sbb = ScoreButtonBehaviour(self._score_button, self.data)

        self._time_button = self._b.get_object('time')
        self._tbb = TimeButtonBehaviour(self._time_button, self.data)

        self._reply_button = self._b.get_object('reply')
        connect_palette(self._reply_button, self._make_reply_palette,
                        recycle_palette=True)

        self._sub_button = self._b.get_object('sub')
        self._sub_button.props.visible = show_subreddit
        if show_subreddit:
            self._subbb = SubButtonBehaviour(self._sub_button, self.data)

        self._b.connect_signals(self)

    def refresh_clicked_cb(self, button):
        self.refresh.emit()

    def read_toggled_cb(self, toggle):
        if toggle.props.active:
            get_reddit_api().read_message(self.data['name'])
            self._read.get_style_context().remove_class('unread')
            self._read.props.active = True
            self._read.props.sensitive = False
            self._read.props.label = 'Read'

    def hide_toggled_cb(self, toggle):
        self.hide_toggled.emit(not toggle.props.active)

    def _make_reply_palette(self):
        palette = _ReplyPopover(self.data)
        palette.get_child().show_all()
        palette.refresh.connect(self.__palette_refresh_cb)
        return palette

    def favorite_toggled_cb(self, button):
        get_reddit_api().set_saved(self.data['name'], button.props.active,
                                   None)

    def __palette_refresh_cb(self, caller):
        self.refresh.emit()


class _ReplyPopover(Gtk.Popover):

    refresh = GObject.Signal('refresh')

    def __init__(self, data, **kwargs):
        Gtk.Popover.__init__(self, **kwargs)
        self.data = data
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(box)

        sw = Gtk.ScrolledWindow()
        sw.set_size_request(500, 300)
        box.add(sw)
        self._textview = Gtk.TextView()
        self._textview.props.wrap_mode = Gtk.WrapMode.WORD
        self._textview.set_size_request(500, 300)
        sw.add(self._textview)

        self._done = Gtk.Button(label='Post Reply')
        self._done.connect('clicked', self.__done_clicked_cb)
        box.add(self._done)

        box.show_all()

    def __done_clicked_cb(self, button):
        self._done.props.label = 'Sending...'
        self._done.props.sensitive = False
        b = self._textview.props.buffer
        text = b.get_text(b.get_start_iter(), b.get_end_iter(), False)
        get_reddit_api().reply(self.data['name'], text, self.__reply_done_cb)

    def __reply_done_cb(self, data):
        self.refresh.emit()
        self.hide()
        self.destroy()


class CommentRow(Gtk.ListBoxRow):

    refresh = GObject.Signal('refresh')
    got_more_comments = GObject.Signal('got-more-comments', arg_types=[object])

    def __init__(self, data, depth, original_poster=None):
        Gtk.ListBoxRow.__init__(self, selectable=False)
        self.data = data
        self._depth = depth
        self._original_poster = original_poster

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._box)
        self._box.show()

        if 'body' in data:
            self._show_normal_comment()
        else:
            # TODO: There is a list of ids in the 'children' (id)
            #       and also the 'parent_id' (fullname) and 'count'
            b = Gtk.Button.new_with_label(
                'Show {} more comments...'.format(data['count']))
            b.connect('clicked', self.__load_more_cb)
            b.get_style_context().add_class('load-more')
            self._box.add(b)
            b.show()

    def __load_more_cb(self, button):
        button.props.sensitive = False
        comments = self.get_toplevel().get_comments_view()
        get_reddit_api().load_more(
            comments.get_link_name(), self.data, self.__loaded_more_cb)

    def __loaded_more_cb(self, comments):
        self.got_more_comments.emit(comments)

    def _show_normal_comment(self):
        self._top = _PostTopBar(self.data,
                                original_poster=self._original_poster)
        self._top.refresh.connect(self.__refresh_cb)
        self._top.hide_toggled.connect(self.__hide_toggled_cb)
        self._box.add(self._top)
        self._top.show()

        body_pango = markdown_to_pango(self.data['body'])
        self._label = SaneLabel(body_pango)
        self._box.add(self._label)
        self._label.show()

        self._sub = None
        self._revealer = None
        if self.data.get('replies'):
            self._revealer = Gtk.Revealer(
                transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
                reveal_child=True
            )
            revealer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self._revealer.add(revealer_box)
            revealer_box.show()
            self._box.add(self._revealer)
            self._revealer.show()

            self._sub = _CommentsView( \
                self.data['replies']['data']['children'],
                depth=self._depth + 1,
                original_poster=self._original_poster)
            self._sub.refresh.connect(self.__refresh_cb)
            revealer_box.add(self._sub)
            self._sub.show()
        else:
            self._top.expand.hide()

    def __refresh_cb(self, caller):
        self.refresh.emit()

    def __hide_toggled_cb(self, top, hidden):
        if self._revealer is not None:
            self._revealer.props.reveal_child = hidden

    def do_activated(self):
        if self._revealer is not None:
            rc = not self._revealer.props.reveal_child
            self._revealer.props.reveal_child = rc
            self._top.expand.props.active = not rc


class MessageRow(Gtk.ListBoxRow):

    def __init__(self, data):
        Gtk.ListBoxRow.__init__(self, selectable=False)
        self.data = data

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._box)
        self._box.show()

        self._top = _PostTopBar(self.data, hideable=False, pm=True)
        self._box.add(self._top)
        self._top.show()

        body_pango = markdown_to_pango(self.data['body'])
        self._label = SaneLabel(body_pango)
        self._box.add(self._label)
        self._label.show()
