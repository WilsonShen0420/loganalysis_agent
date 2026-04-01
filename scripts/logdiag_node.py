#!/usr/bin/env python3
"""Entry point for the LogDiag ROS node."""

from logdiag.node import LogDiagNode


def main():
    node = LogDiagNode()
    node.run()


if __name__ == "__main__":
    main()
