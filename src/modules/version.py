#!/usr/bin/python2.4
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#

#
# Copyright 2008 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.
#

import datetime
import exceptions
import time
import calendar

CONSTRAINT_NONE = 0
CONSTRAINT_AUTO = 50

CONSTRAINT_RELEASE = 100
CONSTRAINT_RELEASE_MAJOR = 101
CONSTRAINT_RELEASE_MINOR = 102

CONSTRAINT_BRANCH = 200
CONSTRAINT_BRANCH_MAJOR = 101
CONSTRAINT_BRANCH_MINOR = 102

CONSTRAINT_SEQUENCE = 300

class IllegalDotSequence(exceptions.Exception):
        def __init__(self, *args):
                exceptions.Exception.__init__(self, *args)

class DotSequence(list):
        """A DotSequence is the typical "x.y.z" string used in software
        versioning.  We define the "major release" value and the "minor release"
        value as the first two numbers in the sequence."""

        def __init__(self, dotstring):
                try:
                        list.__init__(self, map(int, dotstring.split(".")))
                except ValueError:
                        raise IllegalDotSequence(dotstring)

        def __str__(self):
                return ".".join(map(str, self))

        def is_subsequence(self, other):
                """Return true if self is a "subsequence" of other, meaning that
                other and self have identical components, up to the length of
                self's sequence."""

                if len(self) > len(other):
                        return False

                for a, b in zip(self, other):
                        if a != b:
                                return False
                return True

        def is_same_major(self, other):
                """ Test if DotSequences have the same major number """
                return self[0] == other[0]

        def is_same_minor(self, other):
                """ Test if DotSequences have the same major and minor num """
                return self[0] == other[0] and self[1] == other[1]


class IllegalVersion(exceptions.Exception):
        def __init__(self, *args):
                exceptions.Exception.__init__(self, *args)

class Version(object):
        """Version format is release[,build_release]-branch:datetime, which we
        decompose into three DotSequences and a date string.  Time
        representation is in the ISO8601-compliant form "YYYYMMDDTHHMMSSZ",
        referring to the UTC time associated with the version.  The release and
        branch DotSequences are interpreted normally, where v1 < v2 implies that
        v2 is a later release or branch.  The build_release DotSequence records
        the system on which the package binaries were constructed.
        Interpretation of the build_release by the client is that, in the case
        b1 < b2, a b1 package can be run on either b1 or b2 systems,while a b2
        package can only be run on a b2 system."""

        def __init__(self, version_string, build_string):
                # XXX If illegally formatted, raise exception.

                if not version_string:
                        raise IllegalVersion, \
                            "Version cannot be empty."

                timeidx = version_string.find(":")
                if timeidx != -1:
                        timestr = version_string[timeidx + 1:]
                else:
                        timeidx = None
                        timestr = None

                branchidx = version_string.find("-")
                if branchidx != -1:
                        branch = version_string[branchidx + 1:timeidx]
                else:
                        branchidx = timeidx
                        branch = None

                buildidx = version_string.find(",")
                if buildidx != -1:
                        build = version_string[buildidx + 1:branchidx]
                else:
                        buildidx = branchidx
                        build = None

                if buildidx == 0:
                        raise IllegalVersion, \
                            "Versions must have a release value."

                self.release = DotSequence(version_string[:buildidx])

                if branch:
                        self.branch = DotSequence(branch)
                else:
                        self.branch = None

                if build:
                        self.build_release = DotSequence(build)
                else:
                        assert build_string is not None
                        self.build_release = DotSequence(build_string)

                #
                # In 99% of the cases in which we use date and time, it's solely
                # for comparison.  Since the ISO date string lexicographically
                # collates in date order, we just hold onto the string-
                # converting it to anything else is expensive.
                #
                if timestr:
                        if len(timestr) != 16 or timestr[8] != "T" \
                            or timestr[15] != "Z":
                                raise IllegalVersion, \
                                    "Time must be ISO8601 format."
                        try:
                                dateint = int(timestr[0:8])
                                timeint = int(timestr[9:15])
                                datetime.datetime(dateint / 10000,
                                    (dateint / 100) % 100,
                                    dateint % 100,
                                    timeint / 10000,
                                    (timeint / 100) % 100,
                                    timeint % 100)
                        except:
                                raise IllegalVersion, \
                                    "Time must be ISO8601 format."

                        self.timestr = timestr
                else:
                        self.timestr = None

                # raise IllegalVersion

        def compatible_with_build(self, target):
                """target is a DotSequence for the target system."""
                if self.build_release < target:
                        return True
                return False

        def __str__(self):
                outstr = str(self.release) + "," + str(self.build_release)
                if self.branch:
                        outstr += "-" + str(self.branch)
                if self.timestr:
                        outstr += ":" + self.timestr
                return outstr

        def __repr__(self):
                return "<pkg.fmri.Version '%s' at %#x>" % (self, id(self))

        def get_short_version(self):
                branch_str = ""
                if self.branch:
                        branch_str = "-%s" % self.branch
                return "%s%s" % (self.release, branch_str)

        def set_timestamp(self, timestamp=datetime.datetime.utcnow()):
                assert type(timestamp) == datetime.datetime
                assert timestamp.tzname() == None or timestamp.tzname() == "UTC"
                self.timestr = timestamp.strftime("%Y%m%dT%H%M%SZ")

        def get_timestamp(self):
                if not self.timestr:
                        return None
                t = time.strptime(self.timestr, "%Y%m%dT%H%M%SZ")
                return datetime.datetime.utcfromtimestamp(calendar.timegm(t))

        def __ne__(self, other):
                if other == None:
                        return True

                if self.release == other.release and \
                    self.branch == other.branch and \
                    self.timestr == other.timestr:
                        return False
                return True

        def __eq__(self, other):
                if other == None:
                        return False

                if self.release == other.release and \
                    self.branch == other.branch and \
                    self.timestr == other.timestr:
                        return True
                return False

        def __lt__(self, other):
                """Returns True if 'self' comes before 'other', and vice versa.

                If exactly one of the release values of the versions is None,
                then that version is less than the other.  The same applies to
                the branch and timestamp components.
                """
                if other == None:
                        return False

                if self.release < other.release:
                        return True
                if self.release != other.release:
                        return False

                if self.branch < other.branch:
                        return True
                if self.branch != other.branch:
                        return False

                return self.timestr < other.timestr

        def __gt__(self, other):
                """Returns True if 'self' comes after 'other', and vice versa.

                If exactly one of the release values of the versions is None,
                then that version is less than the other.  The same applies to
                the branch and timestamp components.
                """
                if other == None:
                        return True

                if self.release > other.release:
                        return True
                if self.release != other.release:
                        return False

                if self.branch > other.branch:
                        return True
                if self.branch != other.branch:
                        return False

                return self.timestr > other.timestr

        def __cmp__(self, other):
                if self < other:
                        return -1
                if self > other:
                        return 1

                if self.build_release < other.build_release:
                        return -1
                if self.build_release > other.build_release:
                        return 1
                return 0

        def is_successor(self, other, constraint):
                """Evaluate true if self is a successor version to other.

                The loosest constraint is CONSTRAINT_NONE (None is treated
                equivalently, which is a simple test for self > other.  As we
                proceed through the policies we get stricter, depending on the
                selected constraint.

                Slightly less loose is CONSTRAINT_AUTO.  In this case, if any of
                the release, branch, or timestamp components is None, it acts as
                a "don't care" value -- a versioned component always succeeds
                None.

                For CONSTRAINT_RELEASE, self is a successor to other if all of
                the components of other's release match, and there are later
                components of self's version.  The branch and datetime
                components are ignored.

                For CONSTRAINT_RELEASE_MAJOR and CONSTRAINT_RELEASE_MINOR, other
                is effectively truncated to [other[0]] and [other[0], other[1]]
                prior to being treated as for CONSTRAINT_RELEASE.

                Similarly for CONSTRAINT_BRANCH, the release fields of other and
                self are expected to be identical, and then the branches are
                compared as releases were for the CONSTRAINT_RELEASE* policies.
                """

                if constraint == None or constraint == CONSTRAINT_NONE:
                        return self > other

                if constraint == CONSTRAINT_AUTO:
                        release_match = branch_match = date_match = False

                        if other.release and self.release:
                                if other.release.is_subsequence(self.release):
                                        release_match = True
                        elif not other.release:
                                release_match = True

                        if other.branch and self.branch:
                                if other.branch.is_subsequence(self.branch):
                                        branch_match = True
                        elif not other.branch:
                                branch_match = True

                        if self.timestr and other.timestr:
                                if other.timestr == self.timestr:
                                        date_match = True
                        elif not other.timestr:
                                date_match = True

                        return release_match and branch_match and date_match

                if constraint == CONSTRAINT_RELEASE:
                        return other.release.is_subsequence(self.release)

                if constraint == CONSTRAINT_RELEASE_MAJOR:
                        return other.release.is_same_major(self.release)

                if constraint == CONSTRAINT_RELEASE_MINOR:
                        return other.release.is_same_minor(self.release)

                if constraint == CONSTRAINT_BRANCH:
                        return other.branch.is_subsequence(self.branch)

                if constraint == CONSTRAINT_BRANCH_MAJOR:
                        return other.branch.is_same_major(self.branch)

                if constraint == CONSTRAINT_BRANCH_MINOR:
                        return other.branch.is_same_minor(self.branch)

                raise ValueError, "constraint has unknown value"

